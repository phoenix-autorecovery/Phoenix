import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from backend.app.services.sandbox import SandboxExecutionEngine

class ValidationPipeline:
    @staticmethod
    def calculate_patch_hash(patch_content: str) -> str:
        """Returns normalized SHA-256 hash of unified diff."""
        normalized = "\n".join([line.rstrip() for line in patch_content.strip().splitlines()])
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def scan_patch_security(patch_content: str) -> List[Dict[str, Any]]:
        """Static security scan on proposed diff."""
        findings = []
        # Check for dangerous calls inserted
        dangerous_patterns = [
            (r"\beval\(", "Insecure use of eval() detected in patch"),
            (r"\bos\.system\(", "Dangerous shell execution via os.system()"),
            (r"\bsubprocess\.call\(.*shell=True", "Unsafe shell=True subprocess execution"),
            (r"__proto__", "Prototype pollution vector in JS"),
            (r"require\(['\"]child_process['\"]\)", "Direct invocation of child_process"),
            (r"DROP\s+TABLE|DELETE\s+FROM", "Potential destructive SQL statement")
        ]
        
        for line in patch_content.splitlines():
            if line.startswith("+"):  # only inspect added lines
                for pat, msg in dangerous_patterns:
                    if re.search(pat, line):
                        findings.append({
                            "rule": "insecure_code_pattern",
                            "severity": "critical",
                            "message": msg,
                            "line": line[:100]
                        })
        return findings

    @classmethod
    def run_validation(
        cls,
        sandbox_dir: Path,
        patch_content: str,
        test_commands: List[str]
    ) -> Dict[str, Any]:
        """
        Executes static analysis, security scan, and test suite on sandbox directory.
        """
        patch_hash = cls.calculate_patch_hash(patch_content)
        security_findings = cls.scan_patch_security(patch_content)

        if not test_commands:
            return {
                "overall_status": "inconclusive",
                "exit_code": 0,
                "duration_ms": 0,
                "test_output": "No automated test suite detected in project. Static validation only.",
                "security_findings": security_findings,
                "patch_hash": patch_hash,
                "commands_executed": []
            }

        combined_output = []
        overall_exit_code = 0
        total_duration = 0
        all_passed = True

        for cmd_str in test_commands:
            cmd = cmd_str.split()
            # If command is pytest or npm, ensure safe execution
            res = SandboxExecutionEngine.execute_command(cmd, sandbox_dir)
            total_duration += res["duration_ms"]
            output_snippet = (
                f"=== COMMAND: {cmd_str} (Exit: {res['exit_code']}, Time: {res['duration_ms']}ms) ===\n"
                f"{res['stdout']}\n{res['stderr']}\n"
            )
            combined_output.append(output_snippet)

            if res["exit_code"] != 0:
                all_passed = False
                overall_exit_code = res["exit_code"]
                break

        overall_status = "passed" if all_passed and not security_findings else "failed"

        return {
            "overall_status": overall_status,
            "exit_code": overall_exit_code,
            "duration_ms": total_duration,
            "test_output": "\n".join(combined_output),
            "security_findings": security_findings,
            "patch_hash": patch_hash,
            "commands_executed": test_commands
        }
