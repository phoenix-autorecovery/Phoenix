import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List
from backend.app.config import settings

class SandboxExecutionEngine:
    SAFE_ENV_ALLOWLIST = {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE",
        "PYTHONPATH", "NODE_PATH", "LANG", "LC_ALL"
    }

    @classmethod
    def sanitize_environment(cls) -> Dict[str, str]:
        """Scrubs environment variables so no host credentials, Groq keys, or PATs leak."""
        sanitized = {}
        for key, val in os.environ.items():
            if key in cls.SAFE_ENV_ALLOWLIST:
                sanitized[key] = val
        sanitized["CI"] = "true"
        sanitized["PHOENIX_SANDBOX"] = "1"
        return sanitized

    @classmethod
    def create_disposable_copy(cls, source_dir: Path, sandbox_id: str) -> Path:
        """Copies project to disposable sandbox directory."""
        target_dir = settings.SANDBOX_DIR / sandbox_id
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        
        # Copy directory ignoring build artifacts and VCS
        def ignore_patterns(path, names):
            return {n for n in names if n in {".git", ".venv", "node_modules", "__pycache__"}}

        shutil.copytree(source_dir, target_dir, ignore=ignore_patterns)
        return target_dir

    @classmethod
    def cleanup_sandbox(cls, sandbox_dir: Path):
        """Disposes sandbox directory cleanly."""
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir, ignore_errors=True)

    @classmethod
    def execute_command(
        cls,
        command: List[str],
        working_dir: Path,
        timeout_seconds: int = None
    ) -> Dict[str, Any]:
        """
        Executes an allowlisted command in the isolated workspace copy with
        environment scrubbing and strict timeout.
        """
        timeout = timeout_seconds or settings.SANDBOX_TIMEOUT_SECONDS
        sanitized_env = cls.sanitize_environment()

        start_time = time.time()
        try:
            # Direct non-shell array execution to prevent shell injection
            proc = subprocess.run(
                command,
                cwd=str(working_dir),
                env=sanitized_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False
            )
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "duration_ms": duration_ms,
                "timed_out": False
            }
        except subprocess.TimeoutExpired as te:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "exit_code": -1,
                "stdout": te.stdout or "",
                "stderr": f"Execution timed out after {timeout} seconds.",
                "duration_ms": duration_ms,
                "timed_out": True
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Sandbox execution error: {str(e)}",
                "duration_ms": duration_ms,
                "timed_out": False
            }
