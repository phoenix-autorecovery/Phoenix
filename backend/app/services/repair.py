import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.app.services.llm import get_llm_provider
from backend.app.services.sandbox import SandboxExecutionEngine
from backend.app.services.validation import ValidationPipeline
from backend.app.core.policy import PolicyEngine

logger = logging.getLogger("phoenix.repair")

class RepairEngine:
    @staticmethod
    def apply_patch_to_dir(sandbox_dir: Path, patch_content: str) -> bool:
        """
        Applies a unified diff patch to the sandbox directory.
        Uses git apply if git repo exists, or python-based hunk applicator.
        """
        patch_file = sandbox_dir / "candidate.patch"
        patch_file.write_text(patch_content, encoding="utf-8")
        
        # Try git apply first with 3-way fallback
        try:
            res = subprocess.run(
                ["git", "apply", "--ignore-whitespace", "candidate.patch"],
                cwd=str(sandbox_dir),
                capture_output=True,
                text=True,
                timeout=15
            )
            if res.returncode == 0:
                patch_file.unlink(missing_ok=True)
                return True
        except Exception:
            pass

        # Python-based single file replace fallback for clean diff hunks
        try:
            lines = patch_content.splitlines()
            current_target = None
            old_lines = []
            new_lines = []
            
            for line in lines:
                if line.startswith("+++ b/"):
                    current_target = line[6:].strip()
                elif line.startswith("@@"):
                    continue
                elif line.startswith("-") and not line.startswith("---"):
                    old_lines.append(line[1:])
                elif line.startswith("+") and not line.startswith("+++"):
                    new_lines.append(line[1:])

            if current_target and (sandbox_dir / current_target).exists():
                target_path = sandbox_dir / current_target
                content = target_path.read_text(encoding="utf-8")
                old_chunk = "\n".join(old_lines)
                new_chunk = "\n".join(new_lines)
                if old_chunk in content:
                    replaced = content.replace(old_chunk, new_chunk, 1)
                    target_path.write_text(replaced, encoding="utf-8")
                    patch_file.unlink(missing_ok=True)
                    return True
        except Exception as e:
            logger.error(f"Fallback patch application failed: {e}")

        patch_file.unlink(missing_ok=True)
        return False

    @classmethod
    def generate_candidate_repair(
        cls,
        incident_title: str,
        diagnosis_data: Dict[str, Any],
        workspace_dir: Path,
        previous_failure_evidence: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Requests a structured repair plan and minimal unified diff from the LLM adapter.
        """
        relevant_files = diagnosis_data.get("relevant_files", [])
        source_context = {}
        for item in relevant_files:
            file_name = item.get("path") if isinstance(item, dict) else str(item)
            fpath = workspace_dir / file_name
            if fpath.is_file():
                try:
                    source_context[file_name] = fpath.read_text(encoding="utf-8", errors="ignore")[:3000]
                except Exception:
                    pass

        retry_hint = ""
        if previous_failure_evidence:
            retry_hint = f"\nPREVIOUS REPAIR ATTEMPT FAILED WITH:\n{previous_failure_evidence}\nPlease fix the defect and adjust the patch accordingly.\n"

        prompt = f"""
You are the PHOENIX Autonomous Repair Engine. Generate a minimal, high-precision candidate repair for this diagnosed incident.
Respond ONLY in valid JSON matching REPAIR_PLAN_SCHEMA.

INCIDENT: {incident_title}
DIAGNOSIS: {json.dumps(diagnosis_data, indent=2)}
SOURCE FILES: {json.dumps(source_context, indent=2)}
{retry_hint}

REPAIR_PLAN_SCHEMA:
{{
  "hypothesized_cause": "brief summary",
  "intended_behavior": "what the code will do after fix",
  "files_to_modify": ["path/to/file.py"],
  "patch": "--- a/path/to/file.py\\n+++ b/path/to/file.py\\n@@ ... @@\\n",
  "expected_test_outcomes": ["all unit tests pass"],
  "potential_side_effects": "none",
  "security_considerations": "input sanitization and boundary check"
}}
"""
        messages = [
            {"role": "system", "content": "You are a principal software engineer. Produce minimal, exact diffs. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        llm = get_llm_provider()
        raw_response = llm.generate_chat(messages, temperature=0.1)

        try:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
            plan_data = json.loads(cleaned)
        except Exception:
            raise ValueError(f"Model failed to produce valid JSON repair plan. Output: {raw_response[:200]}")

        return plan_data
