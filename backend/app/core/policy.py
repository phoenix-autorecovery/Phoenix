from typing import Dict, Any, List, Tuple
from pydantic import BaseModel

class PolicyDecision(BaseModel):
    allowed: bool
    outcome: str  # approve_for_delivery, reject, request_human_review, request_additional_evidence, block_delivery
    policy_version: str = "1.0.0"
    reasons: List[str]
    risk_level: str  # low, medium, high, critical
    evidence_score: float

class PolicyEngine:
    POLICY_VERSION = "1.0.0"
    
    # Policy thresholds
    MAX_ALLOWED_FILES_CHANGED = 10
    CRITICAL_SECURITY_THRESHOLD = 0
    FORBIDDEN_FILE_PATTERNS = [
        ".env", "id_rsa", "credentials", "secrets.json", ".git/",
        "passwd", "shadow", "auth.key", ".pem"
    ]

    @classmethod
    def evaluate_repair(
        cls,
        files_modified: List[str],
        patch_content: str,
        validation_passed: bool,
        security_findings: List[Dict[str, Any]],
        confidence_score: float,
        has_tests: bool,
        severity: str
    ) -> PolicyDecision:
        reasons = []
        risk_level = "low"
        
        # 1. Gate: Validation outcome check
        if not validation_passed:
            reasons.append("Deterministic validation checks failed.")
            return PolicyDecision(
                allowed=False,
                outcome="reject",
                reasons=reasons,
                risk_level="high",
                evidence_score=confidence_score
            )
        
        # 2. Gate: Sensitive files check
        for f in files_modified:
            for pattern in cls.FORBIDDEN_FILE_PATTERNS:
                if pattern in f.lower():
                    reasons.append(f"Patch attempts to modify restricted sensitive path: {f}")
                    return PolicyDecision(
                        allowed=False,
                        outcome="block_delivery",
                        reasons=reasons,
                        risk_level="critical",
                        evidence_score=confidence_score
                    )
        
        # 3. Gate: Scope of change check
        if len(files_modified) > cls.MAX_ALLOWED_FILES_CHANGED:
            reasons.append(f"Scope of changes exceeds maximum allowed threshold ({len(files_modified)} > {cls.MAX_ALLOWED_FILES_CHANGED} files).")
            risk_level = "high"
        
        # 4. Gate: Security findings check
        critical_findings = [
            f for f in security_findings 
            if f.get("severity", "").lower() in ["critical", "high"]
        ]
        if critical_findings:
            reasons.append(f"Identified {len(critical_findings)} high/critical security scan findings in candidate patch.")
            return PolicyDecision(
                allowed=False,
                outcome="reject",
                reasons=reasons,
                risk_level="critical",
                evidence_score=confidence_score
            )
        
        # 5. Gate: Test availability check
        if not has_tests:
            reasons.append("Project lacks automated test suite; empirical verification inconclusive.")
            risk_level = "medium"
            return PolicyDecision(
                allowed=True,
                outcome="request_human_review",
                reasons=reasons,
                risk_level=risk_level,
                evidence_score=confidence_score
            )
        
        # 6. Gate: Evidence & confidence check
        if confidence_score < 0.65:
            reasons.append(f"Diagnostic confidence score ({confidence_score:.2f}) is below safe autonomous threshold (0.65).")
            return PolicyDecision(
                allowed=True,
                outcome="request_human_review",
                reasons=reasons,
                risk_level="medium",
                evidence_score=confidence_score
            )

        # High severity incident requires human review before pull request
        if severity == "critical":
            reasons.append("Critical severity incident requires explicit human sign-off.")
            return PolicyDecision(
                allowed=True,
                outcome="request_human_review",
                reasons=reasons,
                risk_level="medium",
                evidence_score=confidence_score
            )

        reasons.append("All automated deterministic validation and security policy checks passed.")
        return PolicyDecision(
            allowed=True,
            outcome="approve_for_delivery",
            reasons=reasons,
            risk_level=risk_level,
            evidence_score=confidence_score
        )
