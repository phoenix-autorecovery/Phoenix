import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.incident import Incident, Diagnosis
from backend.app.models.repair import RepairJob, CandidatePatch, ValidationRun, Approval, PullRequestRecord
from backend.app.core.audit import record_audit_event
from backend.app.core.policy import PolicyEngine
from backend.app.services.detector import WorkspaceDefectDetector
from backend.app.services.intelligence import ProjectIntelligenceService
from backend.app.services.diagnosis import DiagnosisEngine
from backend.app.services.repair import RepairEngine
from backend.app.services.sandbox import SandboxExecutionEngine
from backend.app.services.validation import ValidationPipeline
from backend.app.services.delivery import DeliveryService
from backend.app.services.llm import get_llm_provider

logger = logging.getLogger("phoenix.autopilot")

class AutoPilotService:
    @classmethod
    def run_autonomous_recovery(
        cls,
        project: Project,
        db: Session,
        current_user: User,
        auto_apply: bool = True,
        override_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end autonomous self-healing recovery loop:
        1. Automated error & defect detection (syntax, failing tests, crash logs)
        2. Automated AI diagnosis via Groq LLM (LLaMA 3.1 / Qwen)
        3. Automated candidate repair generation
        4. Iterative deterministic verification in isolated sandboxes
        5. Autonomous workspace modification and GitHub PR delivery
        """
        workspace_dir = Path(project.root_path)
        if not workspace_dir.exists():
            return {
                "status": "error",
                "message": f"Project root directory {project.root_path} does not exist."
            }

        active_model = override_model or settings.GROQ_MODEL

        # -------------------------------------------------------------
        # STEP 1: AUTOMATIC DEFECT DETECTION
        # -------------------------------------------------------------
        logger.info(f"Scanning workspace for defects: {project.name} ({workspace_dir})")
        defects = WorkspaceDefectDetector.scan_workspace_for_defects(workspace_dir)

        if not defects:
            project.health_status = "healthy"
            db.commit()
            return {
                "status": "healthy",
                "project_id": project.id,
                "project_name": project.name,
                "defects_count": 0,
                "message": "Zero defects detected. All test suites pass and syntax is valid.",
                "model_used": active_model
            }

        # Take the most critical defect
        defect = defects[0]
        logger.info(f"Detected defect: {defect['title']} (Type: {defect['type']})")

        # -------------------------------------------------------------
        # STEP 2: AUTOMATIC INCIDENT CREATION / DEDUPLICATION
        # -------------------------------------------------------------
        existing_incident = db.query(Incident).filter(
            Incident.project_id == project.id,
            Incident.error_signature == defect["error_signature"],
            Incident.status.in_(["detected", "diagnosing", "diagnosed", "repairing"])
        ).first()

        if existing_incident:
            incident = existing_incident
            incident.stack_trace = defect["stack_trace"]
            incident.raw_log = defect["raw_log"]
        else:
            incident = Incident(
                project_id=project.id,
                title=defect["title"],
                description=f"Automatically detected by PHOENIX Autonomous Watcher ({defect['detected_by']}).",
                stack_trace=defect["stack_trace"],
                raw_log=defect["raw_log"],
                error_signature=defect["error_signature"],
                severity=defect["severity"],
                status="diagnosing"
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)

        record_audit_event(
            db=db,
            action="autopilot.defect_detected",
            resource_type="incident",
            resource_id=incident.id,
            user_id=current_user.id,
            details={"error_signature": defect["error_signature"], "type": defect["type"]}
        )

        # -------------------------------------------------------------
        # STEP 3: AUTOMATED AI DIAGNOSIS (GROQ LLM)
        # -------------------------------------------------------------
        logger.info(f"Running automated diagnosis using Groq LLM ({active_model})...")
        diag_res = DiagnosisEngine.diagnose_incident(
            title=incident.title,
            description=incident.description or "",
            stack_trace=incident.stack_trace or "",
            raw_log=incident.raw_log or "",
            workspace_dir=workspace_dir
        )

        diagnosis = Diagnosis(
            incident_id=incident.id,
            root_cause_hypothesis=diag_res.get("root_cause_hypothesis", "Autonomous diagnosis completed."),
            confidence_score=diag_res.get("confidence_score", 0.9),
            evidence_json=json.dumps(diag_res.get("evidence", [])),
            relevant_files_json=json.dumps(diag_res.get("relevant_files", [])),
            suggested_action=diag_res.get("suggested_action", ""),
            is_repair_safe=diag_res.get("is_repair_safe", True),
            model_used=active_model
        )
        db.add(diagnosis)
        incident.status = "diagnosed"
        db.commit()
        db.refresh(diagnosis)

        record_audit_event(
            db=db,
            action="autopilot.diagnosed",
            resource_type="diagnosis",
            resource_id=diagnosis.id,
            user_id=current_user.id,
            details={"confidence": diagnosis.confidence_score, "model": active_model}
        )

        # -------------------------------------------------------------
        # STEP 4: AUTONOMOUS REPAIR & DETERMINISTIC ITERATION LOOP
        # -------------------------------------------------------------
        logger.info(f"Initiating autonomous repair loop (Max attempts: {settings.MAX_AUTONOMOUS_ATTEMPTS})...")
        repair_job = RepairJob(
            incident_id=incident.id,
            project_id=project.id,
            status="generating",
            max_retries=settings.MAX_AUTONOMOUS_ATTEMPTS
        )
        db.add(repair_job)
        incident.status = "repairing"
        db.commit()
        db.refresh(repair_job)

        profile = ProjectIntelligenceService.analyze_workspace(workspace_dir)
        test_commands = profile.get("test_commands", [])

        previous_failure_evidence = None
        verified_patch: Optional[CandidatePatch] = None
        successful_val_run: Optional[ValidationRun] = None

        for attempt in range(settings.MAX_AUTONOMOUS_ATTEMPTS):
            logger.info(f"Autonomous repair iteration {attempt + 1}/{settings.MAX_AUTONOMOUS_ATTEMPTS}")
            repair_job.retry_count = attempt

            # Generate candidate repair
            repair_plan = RepairEngine.generate_candidate_repair(
                incident_title=incident.title,
                diagnosis_data=diag_res,
                workspace_dir=workspace_dir,
                previous_failure_evidence=previous_failure_evidence
            )

            patch_content = repair_plan.get("patch", "")
            patch_hash = ValidationPipeline.calculate_patch_hash(patch_content)

            candidate_patch = CandidatePatch(
                repair_job_id=repair_job.id,
                patch_content=patch_content,
                diff_summary=repair_plan.get("intended_behavior", "Autonomous repair"),
                files_modified_json=json.dumps(repair_plan.get("files_to_modify", [])),
                patch_hash=patch_hash
            )
            db.add(candidate_patch)
            repair_job.patch_hash = patch_hash
            repair_job.repair_plan_json = json.dumps(repair_plan)
            db.commit()
            db.refresh(candidate_patch)

            # Test in isolated disposable sandbox
            sandbox_id = f"auto_{repair_job.id[:8]}_{attempt}"
            sandbox_dir = SandboxExecutionEngine.create_disposable_copy(workspace_dir, sandbox_id)
            try:
                patch_applied = RepairEngine.apply_patch_to_dir(sandbox_dir, patch_content)
                if not patch_applied:
                    logger.warning(f"Attempt {attempt + 1}: Patch application failed to apply.")
                    previous_failure_evidence = "Patch application failed. Unified diff did not match target files."
                    continue

                val_result = ValidationPipeline.run_validation(sandbox_dir, patch_content, test_commands)
                val_run = ValidationRun(
                    repair_job_id=repair_job.id,
                    candidate_patch_id=candidate_patch.id,
                    overall_status=val_result["overall_status"],
                    exit_code=val_result.get("exit_code", 0),
                    duration_ms=val_result["duration_ms"],
                    test_output=val_result["test_output"],
                    security_findings_json=json.dumps(val_result["security_findings"]),
                    validation_details_json=json.dumps(val_result.get("commands_executed", []))
                )
                db.add(val_run)
                db.commit()
                db.refresh(val_run)

                # Policy Evaluation
                policy_eval = PolicyEngine.evaluate_repair(
                    files_modified=repair_plan.get("files_to_modify", []),
                    patch_content=patch_content,
                    validation_passed=(val_result["overall_status"] == "passed"),
                    security_findings=val_result["security_findings"],
                    confidence_score=diagnosis.confidence_score,
                    has_tests=len(test_commands) > 0,
                    severity=incident.severity
                )

                if policy_eval.allowed and val_result["overall_status"] == "passed":
                    logger.info(f"Attempt {attempt + 1}: Deterministic verification and policy evaluation PASSED!")
                    verified_patch = candidate_patch
                    successful_val_run = val_run
                    break
                else:
                    logger.warning(f"Attempt {attempt + 1}: Verification or policy check failed. Reasons: {policy_eval.reasons}")
                    previous_failure_evidence = f"Tests failed with:\n{val_result['test_output']}\nPolicy reasons: {policy_eval.reasons}"

            finally:
                SandboxExecutionEngine.cleanup_sandbox(sandbox_dir)

        # -------------------------------------------------------------
        # STEP 5: AUTONOMOUS WORKSPACE MODIFICATION
        # -------------------------------------------------------------
        if verified_patch and successful_val_run:
            logger.info(f"Verification successful in sandbox. Generating human approval request for: {repair_job.id}")
            
            # Policy Enforcement: Strictly request human approval (NO auto-approvals)
            repair_job.status = "awaiting_approval"
            incident.status = "repairing"
            
            # Create Pending Approval request
            existing_approval = db.query(Approval).filter(Approval.repair_job_id == repair_job.id).first()
            if existing_approval:
                existing_approval.status = "pending"
                existing_approval.patch_hash = verified_patch.patch_hash
                existing_approval.reviewer_notes = f"Verified in isolated sandbox using {active_model}. Awaiting human cryptographic sign-off."
                approval = existing_approval
            else:
                approval = Approval(
                    repair_job_id=repair_job.id,
                    candidate_patch_id=verified_patch.id,
                    user_id=current_user.id,
                    status="pending",
                    patch_hash=verified_patch.patch_hash,
                    base_commit=repair_job.base_commit,
                    reviewer_notes=f"Deterministic tests PASSED in isolated sandbox using {active_model}. Awaiting human cryptographic sign-off."
                )
                db.add(approval)

            db.commit()

            record_audit_event(
                db=db,
                action="autopilot.approval_requested",
                resource_type="repair_job",
                resource_id=repair_job.id,
                user_id=current_user.id,
                details={
                    "incident_id": incident.id,
                    "patch_hash": verified_patch.patch_hash,
                    "status": "awaiting_approval",
                    "model_used": active_model
                }
            )

            return {
                "status": "awaiting_approval",
                "project_id": project.id,
                "project_name": project.name,
                "incident_id": incident.id,
                "incident_title": incident.title,
                "repair_job_id": repair_job.id,
                "model_used": active_model,
                "patch_hash": verified_patch.patch_hash,
                "patch_diff": verified_patch.patch_content,
                "workspace_modified": False,
                "test_output": successful_val_run.test_output,
                "requires_approval": True,
                "message": f"Deterministic verification PASSED in isolated sandbox using {active_model}. Human cryptographic approval request created: manual sign-off required before repository delivery."
            }

        else:
            logger.warning(f"Autonomous repair failed to verify after {settings.MAX_AUTONOMOUS_ATTEMPTS} attempts.")
            repair_job.status = "failed"
            project.health_status = "critical"
            db.commit()

            record_audit_event(
                db=db,
                action="autopilot.recovery_failed",
                resource_type="project",
                resource_id=project.id,
                user_id=current_user.id,
                details={"incident_id": incident.id, "attempts": settings.MAX_AUTONOMOUS_ATTEMPTS}
            )

            return {
                "status": "failed",
                "project_id": project.id,
                "project_name": project.name,
                "incident_id": incident.id,
                "incident_title": incident.title,
                "repair_job_id": repair_job.id,
                "model_used": active_model,
                "message": f"Autonomous repair could not satisfy deterministic verification after {settings.MAX_AUTONOMOUS_ATTEMPTS} attempts. Escalated for human review."
            }
