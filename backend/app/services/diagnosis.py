import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.app.services.llm import get_llm_provider

class DiagnosisEngine:
    @staticmethod
    def extract_error_signature(stack_trace: Optional[str], raw_log: Optional[str]) -> str:
        """Extracts normalized error signature from trace or log."""
        text = (stack_trace or "") + "\n" + (raw_log or "")
        # Common Python exceptions
        py_match = re.search(r"([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):\s*(.*)", text)
        if py_match:
            return f"{py_match.group(1)}: {py_match.group(2).strip()[:80]}"
        
        # JS/Node exceptions
        js_match = re.search(r"Error:\s*(.*)", text)
        if js_match:
            return f"Error: {js_match.group(1).strip()[:80]}"

        # First line fallback
        first_line = text.strip().split("\n")[0] if text.strip() else "UnknownError"
        return first_line[:100]

    @staticmethod
    def locate_source_files_from_trace(stack_trace: str, workspace_dir: Path) -> List[str]:
        """Locates candidate files inside workspace referenced in trace."""
        if not stack_trace:
            return []
        candidate_files = set()
        # Find file paths like file.py line 12 or at foo.js:34
        matches = re.findall(r'File "([^"]+)", line \d+|at .*? \((.*?):\d+:\d+\)|([a-zA-Z0-9_\-\./\\]+\.(?:py|js|ts|tsx|jsx))', stack_trace)
        for m in matches:
            for item in m:
                if item and not item.startswith("<"):
                    cleaned = item.replace("\\", "/").split("/")[-1]
                    # Check if file exists in workspace
                    for found in workspace_dir.rglob(cleaned):
                        if found.is_file():
                            rel = found.relative_to(workspace_dir).as_posix()
                            if not any(ign in rel for ign in [".git", "node_modules", ".venv"]):
                                candidate_files.add(rel)
        return list(candidate_files)

    @classmethod
    def diagnose_incident(
        cls,
        title: str,
        description: str,
        stack_trace: str,
        raw_log: str,
        workspace_dir: Path
    ) -> Dict[str, Any]:
        """
        Runs software intelligence to analyze error, retrieve relevant source snippets,
        and query the LLM adapter using a structured JSON schema.
        """
        signature = cls.extract_error_signature(stack_trace, raw_log)
        relevant_files = cls.locate_source_files_from_trace(stack_trace, workspace_dir)
        
        # Collect source context safely (up to 3 files, max 200 lines each)
        source_context = {}
        for rel_file in relevant_files[:3]:
            file_path = workspace_dir / rel_file
            if file_path.is_file():
                try:
                    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:200]
                    source_context[rel_file] = "\n".join([f"{i+1}: {l}" for i, l in enumerate(lines)])
                except Exception:
                    pass

        prompt = f"""
You are the PHOENIX Autonomous Diagnosis Engine. Analyze this software incident and output ONLY valid JSON matching DIAGNOSIS_SCHEMA.

INCIDENT DETAILS:
Title: {title}
Description: {description}
Error Signature: {signature}

STACK TRACE / LOGS:
{stack_trace or raw_log or 'No stack trace provided'}

RELEVANT SOURCE CODE SNIPPETS:
{json.dumps(source_context, indent=2)}

DIAGNOSIS_SCHEMA:
{{
  "root_cause_hypothesis": "Clear explanation of the precise defect",
  "confidence_score": 0.85,  // float between 0.0 and 1.0
  "evidence": [
    {{"type": "stack_trace|source_code|log", "observation": "factual evidence"}}
  ],
  "relevant_files": [
    {{"path": "file_path", "lines": [10, 15], "reason": "why this line is relevant"}}
  ],
  "suggested_action": "High-level fix strategy",
  "is_repair_safe": true
}}
"""
        messages = [
            {"role": "system", "content": "You are a senior software systems diagnostics engineer. Always answer with valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        llm = get_llm_provider()
        response_text = llm.generate_chat(messages, temperature=0.1)

        try:
            # Strip markdown json blocks if present
            cleaned = re.sub(r"^```(?:json)?\s*", "", response_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
            diagnosis_data = json.loads(cleaned)
        except Exception:
            # Safe structured fallback
            diagnosis_data = {
                "root_cause_hypothesis": f"Incident triggered by {signature}. Review logs and source context.",
                "confidence_score": 0.5,
                "evidence": [{"type": "raw_log", "observation": signature}],
                "relevant_files": [{"path": f, "lines": [], "reason": "Appeared in stack trace"} for f in relevant_files],
                "suggested_action": "Manually inspect source locations or add more diagnostic logs.",
                "is_repair_safe": False
            }

        return {
            "signature": signature,
            "diagnosis": diagnosis_data,
            "model_used": getattr(llm, "model", "mock")
        }
