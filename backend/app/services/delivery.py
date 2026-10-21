import io
import os
import zipfile
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
        Creates a new repair branch and opens a GitHub Pull Request via GitHub REST API.
        Never touches or commits directly to the default branch.
        """
        token = github_token or settings.GITHUB_TOKEN
        if not token:
            raise HTTPException(
                status_code=400,
                detail="GitHub Personal Access Token or App Token is not configured. Delivery blocked."
            )

        # Parse owner and repo from URL
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

        # 1. Fetch default branch commit SHA
        with httpx.Client(timeout=30.0) as client:
            ref_resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
                headers=headers
            )
            if ref_resp.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to query base branch '{base_branch}': {ref_resp.text}"
                )
            base_sha = ref_resp.json()["object"]["sha"]

            # 2. Create repair branch
            branch_resp = client.post(
                f"https://api.github.com/repos/{owner}/{repo}/git/refs",
                headers=headers,
                json={"ref": f"refs/heads/{branch_name}", "sha": base_sha}
            )
            if branch_resp.status_code not in (200, 201):
                # Branch might already exist, handle gracefully
                pass

            # 3. Create pull request
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
