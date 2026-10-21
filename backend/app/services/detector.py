import ast
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.app.services.intelligence import ProjectIntelligenceService
from backend.app.services.sandbox import SandboxExecutionEngine

logger = logging.getLogger("phoenix.detector")

class WorkspaceDefectDetector:
    """
    Autonomous error and incident detection engine.
    Continuously or on-demand inspects project workspaces for:
    1. Failing test suites (pytest, npm test)
    2. Syntax and AST parsing errors
    3. Runtime unhandled exception logs
    """

    @classmethod
    def scan_workspace_for_defects(cls, workspace_dir: Path) -> List[Dict[str, Any]]:
        defects: List[Dict[str, Any]] = []

        if not workspace_dir.exists():
            return defects

        # 1. AST Syntax Scan on Python files
        syntax_defects = cls._scan_python_syntax(workspace_dir)
        defects.extend(syntax_defects)

        # 2. Test Suite Execution in Isolated Disposable Sandbox
        test_defects = cls._scan_test_suite_failures(workspace_dir)
        defects.extend(test_defects)

        # 3. Workspace Crash Log Inspection
        log_defects = cls._scan_crash_logs(workspace_dir)
        defects.extend(log_defects)

        return defects

    @classmethod
    def _scan_python_syntax(cls, workspace_dir: Path) -> List[Dict[str, Any]]:
        syntax_defects = []
        for py_file in workspace_dir.rglob("*.py"):
            rel_path = py_file.relative_to(workspace_dir).as_posix()
            if any(part in rel_path for part in [".git", ".venv", "__pycache__", "node_modules"]):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                ast.parse(content, filename=rel_path)
            except SyntaxError as e:
                line_text = e.text.strip() if e.text else ""
                stack = f'  File "{rel_path}", line {e.lineno}\n    {line_text}\nSyntaxError: {e.msg}'
                syntax_defects.append({
                    "type": "syntax_error",
                    "title": f"SyntaxError in {rel_path}: {e.msg} (line {e.lineno})",
                    "stack_trace": stack,
                    "raw_log": str(e),
                    "error_signature": f"SyntaxError:{rel_path}:{e.lineno}",
                    "severity": "critical",
                    "detected_by": "ast_syntax_parser",
                    "failing_files": [rel_path]
                })
            except Exception as e:
                logger.warning(f"Could not parse {rel_path}: {e}")

        return syntax_defects

    @classmethod
    def _scan_test_suite_failures(cls, workspace_dir: Path) -> List[Dict[str, Any]]:
        profile = ProjectIntelligenceService.analyze_workspace(workspace_dir)
        test_commands = profile.get("test_commands", [])

        if not test_commands:
            return []

        defects = []
        sandbox_id = f"detect_{uuid.uuid4().hex[:8]}"
        sandbox_dir = SandboxExecutionEngine.create_disposable_copy(workspace_dir, sandbox_id)

        try:
            for cmd_str in test_commands:
                cmd = cmd_str.split()
                res = SandboxExecutionEngine.execute_command(cmd, sandbox_dir, timeout_seconds=30)
                
                # If tests failed
                if res["exit_code"] != 0:
                    combined_output = f"{res['stdout']}\n{res['stderr']}".strip()
                    
                    # Extract error signature and primary error line
                    error_signature = "TestFailure:Unknown"
                    title = f"Test failure detected during automated execution: {cmd_str}"

                    # Python pytest failure pattern
                    py_fail = re.search(r"FAILED\s+([a-zA-Z0-9_\-\./\\]+\.py::[a-zA-Z0-9_]+)\s+-\s+(.*)", combined_output)
                    error_match = re.search(r"(TypeError|AssertionError|ZeroDivisionError|ValueError|KeyError|AttributeError|IndexError):\s*(.*)", combined_output)
                    
                    if error_match:
                        err_type = error_match.group(1)
                        err_msg = error_match.group(2).strip()[:80]
                        title = f"{err_type}: {err_msg}"
                        error_signature = f"{err_type}:{err_msg}"
                    elif py_fail:
                        test_name = py_fail.group(1)
                        reason = py_fail.group(2).strip()[:80]
                        title = f"Test Failed: {test_name} - {reason}"
                        error_signature = f"Fail:{test_name}"

                    # Locate files mentioned in failure trace
                    failing_files = []
                    matches = re.findall(r'([a-zA-Z0-9_\-\./\\]+\.(?:py|js|ts))\b', combined_output)
                    for m in matches:
                        clean_m = m.replace("\\", "/")
                        if (workspace_dir / clean_m).is_file() and clean_m not in failing_files:
                            failing_files.append(clean_m)

                    defects.append({
                        "type": "test_failure",
                        "title": title,
                        "stack_trace": combined_output[-4000:],  # preserve tail of stack trace
                        "raw_log": combined_output[-8000:],
                        "error_signature": error_signature[:250],
                        "severity": "critical" if res["exit_code"] != 1 else "high",
                        "detected_by": f"sandbox_runner:{cmd_str}",
                        "failing_files": failing_files
                    })
        finally:
            SandboxExecutionEngine.cleanup_sandbox(sandbox_dir)

        return defects

    @classmethod
    def _scan_crash_logs(cls, workspace_dir: Path) -> List[Dict[str, Any]]:
        log_defects = []
        for log_file in workspace_dir.glob("*.log"):
            rel_path = log_file.name
            try:
                content = log_file.read_text(encoding="utf-8", errors="ignore")
                if "Traceback (most recent call last):" in content or "Unhandled rejection" in content:
                    # Extract last traceback
                    tb_match = re.findall(r"(Traceback \(most recent call last\):[\s\S]*?(?:[A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):.*)", content)
                    if tb_match:
                        latest_tb = tb_match[-1]
                        err_line = latest_tb.strip().splitlines()[-1]
                        log_defects.append({
                            "type": "crash_log",
                            "title": f"Crash Log Traceback: {err_line[:100]}",
                            "stack_trace": latest_tb[-3000:],
                            "raw_log": content[-5000:],
                            "error_signature": f"LogCrash:{err_line[:80]}",
                            "severity": "high",
                            "detected_by": f"log_scanner:{rel_path}",
                            "failing_files": []
                        })
            except Exception:
                pass

        return log_defects
