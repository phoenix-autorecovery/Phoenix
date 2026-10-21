import hashlib
import os
import re
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, List
from urllib.parse import urlparse
from fastapi import HTTPException
from backend.app.config import settings

SECRET_PATTERNS = [
    (r"(?i)api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", "API Key"),
    (r"(?i)secret[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", "Secret Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private Key"),
    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9/+]{40})['\"]?", "AWS Secret Key")
]

class IngestionService:
    @staticmethod
    def calculate_dir_fingerprint(directory_path: Path) -> Tuple[str, int, int]:
        """Calculates a deterministic SHA256 fingerprint over all non-ignored project files."""
        hasher = hashlib.sha256()
        file_count = 0
        total_size = 0
        
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}]
            for file in sorted(files):
                file_path = Path(root) / file
                try:
                    rel_path = file_path.relative_to(directory_path).as_posix()
                    size = file_path.stat().st_size
                    hasher.update(rel_path.encode("utf-8"))
                    hasher.update(str(size).encode("utf-8"))
                    file_count += 1
                    total_size += size
                except Exception:
                    continue
                    
        return hasher.hexdigest(), file_count, total_size

    @staticmethod
    def scan_for_secrets(directory_path: Path) -> List[Dict[str, Any]]:
        findings = []
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "__pycache__"}]
            for file in files:
                file_path = Path(root) / file
                if file_path.stat().st_size > 1024 * 1024:  # skip files > 1MB
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for pattern, name in SECRET_PATTERNS:
                        matches = re.findall(pattern, content)
                        if matches:
                            findings.append({
                                "file": file_path.relative_to(directory_path).as_posix(),
                                "secret_type": name,
                                "count": len(matches)
                            })
                except Exception:
                    continue
        return findings

    @classmethod
    def extract_zip(cls, zip_bytes: bytes, target_dir: Path) -> Dict[str, Any]:
        """
        Safely extracts a ZIP archive with strict ZIP-Slip, decompression ratio,
        and symlink attack protections.
        """
        if len(zip_bytes) > settings.MAX_ARCHIVE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Archive exceeds maximum permitted size of {settings.MAX_ARCHIVE_SIZE_BYTES // (1024*1024)}MB"
            )

        target_dir.mkdir(parents=True, exist_ok=True)
        zip_temp_path = target_dir / "uploaded.zip"
        zip_temp_path.write_bytes(zip_bytes)

        total_uncompressed = 0
        file_count = 0

        try:
            with zipfile.ZipFile(zip_temp_path, "r") as zf:
                # Security checks across all entries
                for member in zf.infolist():
                    file_count += 1
                    total_uncompressed += member.file_size
                    
                    if file_count > settings.MAX_FILE_COUNT:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Archive contains too many files (limit: {settings.MAX_FILE_COUNT})"
                        )
                    if total_uncompressed > settings.MAX_UNCOMPRESSED_SIZE_BYTES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Decompressed archive size exceeds limit ({settings.MAX_UNCOMPRESSED_SIZE_BYTES // (1024*1024)}MB)"
                        )

                    # Reject symlinks
                    # In standard ZIP, unix mode is in upper 16 bits of external_attr
                    if (member.external_attr >> 16) & 0o120000 == 0o120000:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Security rejection: Symlinks are not permitted in project archives ({member.filename})"
                        )

                    # ZIP Slip prevention
                    resolved_dest = (target_dir / member.filename).resolve()
                    if not str(resolved_dest).startswith(str(target_dir.resolve())):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Security rejection: Path traversal detected in archive entry: {member.filename}"
                        )

                zf.extractall(target_dir)
        finally:
            if zip_temp_path.exists():
                zip_temp_path.unlink()

        # Handle nested root directories (e.g., zip contains single top-level folder)
        entries = [e for e in target_dir.iterdir() if e.name not in {".git"}]
        if len(entries) == 1 and entries[0].is_dir():
            nested_dir = entries[0]
            for item in nested_dir.iterdir():
                shutil.move(str(item), str(target_dir / item.name))
            nested_dir.rmdir()

        fingerprint, count, size = cls.calculate_dir_fingerprint(target_dir)
        secrets = cls.scan_for_secrets(target_dir)

        return {
            "root_path": str(target_dir),
            "fingerprint": fingerprint,
            "file_count": count,
            "total_size": size,
            "secrets_found": secrets
        }

    @classmethod
    def clone_github_repo(cls, repo_url: str, target_dir: Path, branch: str = None) -> Dict[str, Any]:
        """
        Clones a public or authorized GitHub repository with SSRF prevention and commit pinning.
        """
        parsed = urlparse(repo_url)
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise HTTPException(
                status_code=400,
                detail="Security rejection: Only valid https://github.com/ URLs are permitted."
            )

        clean_path = parsed.path.strip("/")
        if not re.match(r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$", clean_path.replace(".git", "")):
            raise HTTPException(
                status_code=400,
                detail="Invalid repository format. Expected https://github.com/owner/repository"
            )

        target_dir.mkdir(parents=True, exist_ok=True)
        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd.extend(["-b", branch])
        clone_cmd.extend([repo_url, str(target_dir)])

        try:
            res = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=True
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Git clone operation timed out after 120s.")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=400, detail=f"Git clone failed: {e.stderr.strip()}")

        # Record exact commit SHA
        try:
            sha_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                check=True
            )
            commit_sha = sha_res.stdout.strip()
        except Exception:
            commit_sha = "unknown"

        fingerprint, count, size = cls.calculate_dir_fingerprint(target_dir)
        secrets = cls.scan_for_secrets(target_dir)

        return {
            "root_path": str(target_dir),
            "commit_sha": commit_sha,
            "fingerprint": fingerprint,
            "file_count": count,
            "total_size": size,
            "secrets_found": secrets
        }
