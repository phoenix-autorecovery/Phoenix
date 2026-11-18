"""
Security Agent
Conducts automated AST & static analysis on patch diff for security vulnerabilities, forbidden vectors, and injections.
"""
import logging
import re
from typing import Any, Dict, List
from backend.app.services.agents.base import BaseAgent, AgentContext

logger = logging.getLogger("phoenix.agents.security")

FORBIDDEN_PATTERNS = [
    (r"\beval\s*\(", "Use of arbitrary eval() execution", "CRITICAL"),
    (r"\bexec\s*\(", "Use of arbitrary exec() execution", "CRITICAL"),
    (r"os\.system\s*\(", "Direct shell command execution via os.system", "HIGH"),
    (r"subprocess\.(Popen|run|call)\s*\(.*shell\s*=\s*True", "Shell injection risk with shell=True", "CRITICAL"),
    (r"__import__\s*\(", "Dynamic module import injection", "HIGH"),
    (r"DROP\s+TABLE", "Destructive SQL operation detected", "HIGH"),
    (r"(api[_-]?key|secret|password)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "Hardcoded credential or token detected", "CRITICAL"),
]


class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SecurityAgent",
            role="AST Vulnerability & Static Injection Auditor"
        )

    async def run(self, context: AgentContext, db_session: Any) -> Dict[str, Any]:
        patch = context.state.get("patch")
        diff_text = getattr(patch, "diff_content", "") if patch else ""

        context.log(self.name, "security_scan_start", "Auditing candidate diff against forbidden execution vectors...")

        findings: List[Dict[str, str]] = []
        for pattern, desc, severity in FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, diff_text, flags=re.IGNORECASE)
            if matches:
                findings.append({
                    "pattern": pattern,
                    "description": desc,
                    "severity": severity,
                    "occurrences": len(matches)
                })

        has_critical = any(f["severity"] == "CRITICAL" for f in findings)
        risk_score = 0
        for f in findings:
            risk_score += 40 if f["severity"] == "CRITICAL" else 20
        risk_score = min(risk_score, 100)

        if has_critical:
            context.log(
                self.name,
                "security_veto",
                f"SECURITY VETO: {len(findings)} dangerous patterns identified! Candidate diff blocked.",
                level="error",
                data={"findings": findings, "risk_score": risk_score}
            )
            return {
                "security_cleared": False,
                "security_veto": True,
                "security_findings": findings,
                "risk_score": risk_score
            }
        else:
            context.log(
                self.name,
                "security_cleared",
                f"Diff static audit passed. Risk score: {risk_score}/100. No critical vulnerabilities found.",
                level="success",
                data={"findings": findings, "risk_score": risk_score}
            )
            return {
                "security_cleared": True,
                "security_veto": False,
                "security_findings": findings,
                "risk_score": risk_score
            }
