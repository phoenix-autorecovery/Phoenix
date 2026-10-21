import json
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.incident import Incident, Diagnosis
from backend.app.models.repair import RepairJob, CandidatePatch, ValidationRun, Approval
from backend.app.schemas.repair import RepairJobCreate, RepairJobResponse, ValidationRunResponse
from backend.app.core.security import get_current_user
from backend.app.core.audit import record_audit_event
from backend.app.core.policy import PolicyEngine
from backend.app.services.repair import RepairEngine
from backend.app.services.sandbox import SandboxExecutionEngine
from backend.app.services.validation import ValidationPipeline
from backend.app.services.intelligence import ProjectIntelligenceService

router = APIRouter(prefix="/repairs", tags=["Repair Engine & Validation"])

@router.post("", response_model=RepairJobResponse)
def create_repair_job(req: RepairJobCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    incident = db.query(Incident).join(Project).filter(Incident.id == req.incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if incident.project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.incident_id == incident.id).order_by(Diagnosis.created_at.desc()).first()
    if not diagnosis:
        raise HTTPException(status_code=400, detail="Cannot repair an incident before diagnosis has been performed.")

    repair_job = RepairJob(
        incident_id=incident.id,
        project_id=incident.project_id,
        status="generating"
    )
    db.add(repair_job)
    incident.status = "repairing"
    db.commit()
    db.refresh(repair_job)

    workspace_dir = Path(incident.project.root_path)
    diagnosis_dict = {
        "root_cause_hypothesis": diagnosis.root_cause_hypothesis,
        "confidence_score": diagnosis.confidence_score,
        "relevant_files": json.loads(diagnosis.relevant_files_json or "[]"),
        "suggested_action": diagnosis.suggested_action
    }

    try:
        plan = RepairEngine.generate_candidate_repair(
            incident_title=incident.title,
            diagnosis_data=diagnosis_dict,
            workspace_dir=workspace_dir
        )
        patch_text = plan.get("patch", "")
        files_mod = plan.get("files_to_modify", [])
        patch_hash = ValidationPipeline.calculate_patch_hash(patch_text)

        candidate_patch = CandidatePatch(
            repair_job_id=repair_job.id,
            patch_content=patch_text,
            diff_summary=plan.get("intended_behavior", ""),
            files_modified_json=json.dumps(files_mod),
            patch_hash=patch_hash
        )
        db.add(candidate_patch)

        repair_job.patch_hash = patch_hash
        repair_job.base_commit = incident.project.content_fingerprint
        repair_job.repair_plan_json = json.dumps(plan)
        repair_job.status = "validating"
        db.commit()

        # Run automated validation immediately
        sandbox_id = f"sandbox_{repair_job.id[:8]}"
        sandbox_dir = SandboxExecutionEngine.create_disposable_copy(workspace_dir, sandbox_id)
        
        try:
            # Apply candidate patch to disposable copy
            applied = RepairEngine.apply_patch_to_dir(sandbox_dir, patch_text)
            intel = ProjectIntelligenceService.analyze_workspace(sandbox_dir)
            test_cmds = intel.get("test_commands", [])

            if not applied:
                val_result = {
                    "overall_status": "failed",
                    "exit_code": 1,
                    "duration_ms": 10,
                    "test_output": "Failed to apply candidate diff cleanly to disposable copy.",
                    "security_findings": [],
                    "patch_hash": patch_hash
                }
            else:
                val_result = ValidationPipeline.run_validation(sandbox_dir, patch_text, test_cmds)

            val_run = ValidationRun(
                repair_job_id=repair_job.id,
                candidate_patch_id=candidate_patch.id,
                overall_status=val_result["overall_status"],
                exit_code=val_result["exit_code"],
                duration_ms=val_result["duration_ms"],
                test_output=val_result["test_output"],
                security_findings_json=json.dumps(val_result["security_findings"])
            )
            db.add(val_run)

            # Evaluate Policy Gate
            policy = PolicyEngine.evaluate_repair(
                files_modified=files_mod,
                patch_content=patch_text,
                validation_passed=(val_result["overall_status"] == "passed"),
                security_findings=val_result["security_findings"],
                confidence_score=diagnosis.confidence_score,
                has_tests=bool(test_cmds),
                severity=incident.severity
            )

            if policy.allowed and policy.outcome in ["approve_for_delivery", "request_human_review"]:
                repair_job.status = "awaiting_approval"
            else:
                repair_job.status = "rejected"
                repair_job.error_message = "; ".join(policy.reasons)

            db.commit()

        finally:
            SandboxExecutionEngine.cleanup_sandbox(sandbox_dir)

    except Exception as e:
        repair_job.status = "failed"
        repair_job.error_message = str(e)
        db.commit()

    db.refresh(repair_job)
    record_audit_event(
        db=db,
        action="repair.created",
        resource_type="repair_job",
        resource_id=repair_job.id,
        user_id=current_user.id,
        details={"status": repair_job.status, "hash": repair_job.patch_hash}
    )

    return _format_repair_job(repair_job)

@router.get("", response_model=List[RepairJobResponse])
def list_repairs(incident_id: str = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(RepairJob).join(Project)
    if incident_id:
        query = query.filter(RepairJob.incident_id == incident_id)
    if current_user.role != "admin":
        query = query.filter(Project.user_id == current_user.id)
    jobs = query.order_by(RepairJob.created_at.desc()).all()
    return [_format_repair_job(j) for j in jobs]

@router.get("/{repair_id}", response_model=RepairJobResponse)
def get_repair_job(repair_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(RepairJob).join(Project).filter(RepairJob.id == repair_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Repair job not found.")
    if job.project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    return _format_repair_job(job)

@router.get("/{repair_id}/diff")
def get_repair_diff(repair_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == repair_id).order_by(CandidatePatch.created_at.desc()).first()
    if not patch:
        raise HTTPException(status_code=404, detail="No candidate patch found for this repair job.")
    return {
        "patch_hash": patch.patch_hash,
        "patch_content": patch.patch_content,
        "diff_summary": patch.diff_summary,
        "files_modified": json.loads(patch.files_modified_json or "[]")
    }

def _format_repair_job(job: RepairJob) -> dict:
    return {
        "id": job.id,
        "incident_id": job.incident_id,
        "project_id": job.project_id,
        "status": job.status,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "patch_hash": job.patch_hash,
        "base_commit": job.base_commit,
        "repair_plan": json.loads(job.repair_plan_json) if job.repair_plan_json else None,
        "error_message": job.error_message,
        "candidate_patches": [
            {
                "id": cp.id,
                "repair_job_id": cp.repair_job_id,
                "patch_content": cp.patch_content,
                "diff_summary": cp.diff_summary,
                "files_modified": json.loads(cp.files_modified_json or "[]"),
                "patch_hash": cp.patch_hash,
                "created_at": cp.created_at
            }
            for cp in job.candidate_patches
        ],
        "validation_runs": [
            {
                "id": vr.id,
                "repair_job_id": vr.repair_job_id,
                "candidate_patch_id": vr.candidate_patch_id,
                "overall_status": vr.overall_status,
                "exit_code": vr.exit_code,
                "duration_ms": vr.duration_ms,
                "test_output": vr.test_output,
                "security_findings": json.loads(vr.security_findings_json or "[]"),
                "validation_details": json.loads(vr.validation_details_json or "{}") if vr.validation_details_json else None,
                "ran_at": vr.ran_at
            }
            for vr in job.validation_runs
        ],
        "approvals": [
            {
                "id": a.id,
                "repair_job_id": a.repair_job_id,
                "candidate_patch_id": a.candidate_patch_id,
                "user_id": a.user_id,
                "status": a.status,
                "patch_hash": a.patch_hash,
                "base_commit": a.base_commit,
                "reviewer_notes": a.reviewer_notes,
                "decided_at": a.decided_at,
                "created_at": a.created_at
            }
            for a in job.approvals
        ],
        "pull_requests": [
            {
                "id": pr.id,
                "repair_job_id": pr.repair_job_id,
                "repository_url": pr.repository_url,
                "branch_name": pr.branch_name,
                "pr_number": pr.pr_number,
                "pr_url": pr.pr_url,
                "status": pr.status,
                "created_at": pr.created_at
            }
            for pr in job.pull_requests
        ],
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }
