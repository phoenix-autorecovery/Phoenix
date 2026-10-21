import io
import os
import zipfile
import subprocess
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import HTTPException
from backend.app.config import settings

class DeliveryService:
    @staticmethod
    def generate_patch_file(patch_content: str) -> bytes:
        """Returns candidate patch file as bytes."""
        return patch_content.encode("utf-8")

    @classmethod
    def generate_repaired_zip(cls, repaired_dir: Path) -> io.BytesIO:
        """Packages repaired project directory into an in-memory ZIP archive."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(repaired_dir):
                dirs[:] = [d for d in dirs if d not in {".git", ".venv", "node_modules", "__pycache__"}]
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(repaired_dir).as_posix()
                    zf.write(file_path, arcname=rel_path)
        zip_buffer.seek(0)
        return zip_buffer

    @classmethod
    def push_workspace_to_github(
        cls,
        workspace_dir: Path,
        repo_url: str,
        branch_name: str,
        commit_message: str,
        github_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Commits files in the workspace and pushes directly to a remote GitHub branch
        using authenticated HTTPS without ever committing credentials to git config.
        """
        token = github_token or settings.GITHUB_TOKEN
        if not token:
            raise HTTPException(
                status_code=400,
                detail="GitHub Personal Access Token is not configured. Delivery blocked."
            )

        # Parse owner and repo from URL
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid GitHub repository URL format.")
        owner = parts[-2]
        repo = parts[-1].replace(".git", "")

        authenticated_url = f"https://{token}@github.com/{owner}/{repo}.git"

        # Initialize git if needed
        if not (workspace_dir / ".git").exists():
            subprocess.run(["git", "init"], cwd=str(workspace_dir), check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "PHOENIX Autonomous Agent"], cwd=str(workspace_dir), check=True)
            subprocess.run(["git", "config", "user.email", "phoenix-autorecovery@users.noreply.github.com"], cwd=str(workspace_dir), check=True)

        try:
            # Checkout or create branch
            subprocess.run(["git", "checkout", "-B", branch_name], cwd=str(workspace_dir), capture_output=True, check=True)
            subprocess.run(["git", "add", "-A"], cwd=str(workspace_dir), capture_output=True, check=True)
            
            # Commit changes (allow empty if already up to date)
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=str(workspace_dir),
                capture_output=True
            )

            # Push branch to remote
            push_res = subprocess.run(
                ["git", "push", authenticated_url, f"{branch_name}:{branch_name}", "--force"],
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            if push_res.returncode != 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Git push rejected by remote ({owner}/{repo}): {push_res.stderr.strip()}"
                )

            return {
                "owner": owner,
                "repo": repo,
                "branch_name": branch_name,
                "status": "pushed"
            }
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Git push timed out after 60s.")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Failed to push branch: {str(e)}")

    @classmethod
    def create_github_pull_request(
        cls,
        repo_url: str,
        base_branch: str,
        branch_name: str,
        title: str,
        body: str,
        github_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a GitHub Pull Request comparing branch_name against base_branch via GitHub REST API.
        Never touches or commits directly to the default branch.
        """
        token = github_token or settings.GITHUB_TOKEN
        if not token:
            raise HTTPException(
                status_code=400,
                detail="GitHub Personal Access Token is not configured. Delivery blocked."
            )

        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid GitHub repository URL format.")
        owner = parts[-2]
        repo = parts[-1].replace(".git", "")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PHOENIX-Software-Recovery-Platform"
        }

        with httpx.Client(timeout=30.0) as client:
            # Create pull request
            pr_resp = client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers=headers,
                json={
                    "title": title,
                    "head": branch_name,
                    "base": base_branch,
                    "body": body,
                    "maintainer_can_modify": True
                }
            )

            # If PR already exists, fetch existing PR details
            if pr_resp.status_code == 422 and "A pull request already exists" in pr_resp.text:
                existing_res = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls?head={owner}:{branch_name}&state=open",
                    headers=headers
                )
                if existing_res.status_code == 200 and existing_res.json():
                    pr_data = existing_res.json()[0]
                    return {
                        "branch_name": branch_name,
                        "pr_number": pr_data.get("number"),
                        "pr_url": pr_data.get("html_url"),
                        "status": "existing"
                    }

            if pr_resp.status_code not in (200, 201):
                raise HTTPException(
                    status_code=400,
                    detail=f"GitHub PR creation failed ({pr_resp.status_code}): {pr_resp.text}"
                )

            pr_data = pr_resp.json()
            return {
                "branch_name": branch_name,
                "pr_number": pr_data.get("number"),
                "pr_url": pr_data.get("html_url"),
                "status": "created"
            }
