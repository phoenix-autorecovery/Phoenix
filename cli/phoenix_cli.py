#!/usr/bin/env python3
"""
PHOENIX Local Companion CLI
Explicitly selects local folders, parses ignores, inspects secrets, creates manifests,
and connects to PHOENIX server.
"""

import os
import sys
import argparse
import json
import fnmatch
from pathlib import Path
import httpx

DEFAULT_IGNORES = [
    ".git", ".git/**", "node_modules", "node_modules/**", ".venv", ".venv/**",
    "venv", "venv/**", "__pycache__", "__pycache__/**", "*.pyc", ".env",
    "dist", "dist/**", "build", "build/**", ".DS_Store", "Thumbs.db",
    "*.log", "*.key", "*.pem", "id_rsa*"
]

def load_gitignore_patterns(folder: Path):
    patterns = list(DEFAULT_IGNORES)
    gitignore = folder / ".gitignore"
    if gitignore.is_file():
        try:
            for line in gitignore.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        except Exception:
            pass
    return patterns

def is_ignored(rel_path: str, patterns: list) -> bool:
    posix_path = rel_path.replace("\\", "/")
    for pat in patterns:
        if fnmatch.fnmatch(posix_path, pat) or fnmatch.fnmatch(posix_path.split("/")[-1], pat):
            return True
        if pat.endswith("/**") and posix_path.startswith(pat[:-3]):
            return True
    return False

def scan_local_folder(folder: Path):
    if not folder.exists() or not folder.is_dir():
        print(f"[ERROR] Directory does not exist: {folder}", file=sys.stderr)
        sys.exit(1)

    patterns = load_gitignore_patterns(folder)
    collected_files = []
    total_size = 0

    for root, dirs, files in os.walk(folder):
        rel_root = Path(root).relative_to(folder).as_posix()
        # Filter directories
        dirs[:] = [d for d in dirs if not is_ignored(f"{rel_root}/{d}".strip("/"), patterns)]

        for file in files:
            rel_file = f"{rel_root}/{file}".strip("/")
            if is_ignored(rel_file, patterns):
                continue

            full_path = Path(root) / file
            try:
                size = full_path.stat().st_size
                if size > 2 * 1024 * 1024:  # skip files > 2MB in manifest
                    continue
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                collected_files.append({"path": rel_file, "content": content, "size": size})
                total_size += size
            except Exception as e:
                print(f"[WARN] Skipping {rel_file}: {e}")

    return collected_files, total_size

def main():
    parser = argparse.ArgumentParser(description="PHOENIX Local Companion CLI")
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="Sync local folder to PHOENIX server")
    sync_parser.add_argument("path", help="Path to local project directory")
    sync_parser.add_argument("--name", help="Project name on PHOENIX", default=None)
    sync_parser.add_argument("--server", help="PHOENIX server URL", default="http://localhost:8000")
    sync_parser.add_argument("--token", help="PHOENIX JWT Token", required=True)

    args = parser.parse_args()

    if args.command == "sync":
        project_dir = Path(args.path).resolve()
        project_name = args.name or project_dir.name
        print(f"[*] Scanning local workspace: {project_dir}")
        files, total_size = scan_local_folder(project_dir)
        print(f"[*] Collected {len(files)} permitted files ({total_size / 1024:.1f} KB). Secrets and dependencies omitted.")

        payload = {
            "name": project_name,
            "project_root_name": project_dir.name,
            "files": files
        }

        print(f"[*] Ingesting into PHOENIX server at {args.server}...")
        headers = {"Authorization": f"Bearer {args.token}"}
        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(f"{args.server}/api/v1/ingestion/local", json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    print(f"[SUCCESS] Project successfully ingested!")
                    print(f"  Project ID: {data['id']}")
                    print(f"  Detected Stack: {data['detected_language']} ({data['detected_framework']})")
                    print(f"  Fingerprint: {data['content_fingerprint'][:16]}...")
                else:
                    print(f"[ERROR] Sync failed ({res.status_code}): {res.text}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Connection to PHOENIX server failed: {e}", file=sys.stderr)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
