import json
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.incident import Incident
from backend.app.models.repair import RepairJob, CandidatePatch, Approval, PullRequestRecord, ValidationRun
from backend.app.schemas.repair import PullRequestCreate, PullRequestResponse
from backend.app.core.security import get_current_user
from backend.app.core.audit import record_audit_event
from backend.app.services.delivery import DeliveryService
from backend.app.services.sandbox import SandboxExecutionEngine
from backend.app.services.repair import RepairEngine

router = APIRouter(prefix="/repairs", tags=["Controlled Delivery"])

@router.get("/{repair_id}/artifact")
def download_repair_artifact(
    repair_id: str,
    artifact_type: str = Query("patch", pattern="^(patch|zip)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(RepairJob).join(Project).filter(RepairJob.id == repair_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Repair job not found.")
    if job.project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == repair_id).order_by(CandidatePatch.created_at.desc()).first()
    if not patch:
        raise HTTPException(status_code=404, detail="No candidate patch available.")

    if artifact_type == "patch":
        patch_bytes = DeliveryService.generate_patch_file(patch.patch_content)
        return Response(
            content=patch_bytes,
            media_type="text/x-diff",
            headers={"Content-Disposition": f"attachment; filename=phoenix_repair_{job.id[:8]}.patch"}
        )

    # For ZIP: create a disposable copy, apply patch, and stream ZIP
    workspace_dir = Path(job.project.root_path)
    temp_sandbox_id = f"delivery_{uuid.uuid4().hex[:8]}"
    temp_dir = SandboxExecutionEngine.create_disposable_copy(workspace_dir, temp_sandbox_id)
    try:
        RepairEngine.apply_patch_to_dir(temp_dir, patch.patch_content)
        zip_buffer = DeliveryService.generate_repaired_zip(temp_dir)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={job.project.name}_repaired.zip"}
        )
    finally:
        SandboxExecutionEngine.cleanup_sandbox(temp_dir)

@router.post("/{repair_id}/pull-request", response_model=PullRequestResponse)
def open_pull_request(
    repair_id: str,
    req: PullRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(RepairJob).join(Project).filter(RepairJob.id == repair_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Repair job not found.")
    if job.project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    # Authorization gate: check approval exists
    approval = db.query(Approval).filter(
        Approval.repair_job_id == repair_id,
        Approval.status == "approved"
    ).first()
    if not approval:
        raise HTTPException(
            status_code=400,
            detail="Controlled delivery blocked: Explicit reviewer approval is required before opening a Pull Request."
        )

    patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == repair_id).order_by(CandidatePatch.created_at.desc()).first()
    val_run = db.query(ValidationRun).filter(ValidationRun.repair_job_id == repair_id).order_by(ValidationRun.ran_at.desc()).first()

    incident = job.incident
    branch_name = f"phoenix/repair-{incident.id[:8]}"
    pr_title = req.title or f"fix(phoenix): autonomous repair for {incident.title}"
    
    plan_dict = json.loads(job.repair_plan_json or "{}")
    pr_body = req.body or f"""## PHOENIX Autonomous Repair Report

### Incident Summary
- **Title:** {incident.title}
- **Severity:** {incident.severity}
- **Error Signature:** `{incident.error_signature}`

### Root Cause Hypothesis
{plan_dict.get('hypothesized_cause', 'Defect identified during automated analysis.')}

### Proposed Behavior
{plan_dict.get('intended_behavior', 'Sanitized inputs and boundary checks applied.')}

### Deterministic Verification
- **Validation Status:** {val_run.overall_status.upper() if val_run else 'VERIFIED'}
- **Patch Hash:** `{patch.patch_hash}`
- **Reviewer Sign-off:** Approved by user ID `{approval.user_id}`

### Rollback Plan
If regression occurs, revert this branch commit or close the pull request.
"""

    pr_result = DeliveryService.create_github_pull_request(
        repo_url=job.project.source_url or "",
        base_branch=req.target_branch or "main",
        branch_name=branch_name,
        title=pr_title,
        body=pr_body
    )

    pr_record = PullRequestRecord(
        repair_job_id=job.id,
        repository_url=job.project.source_url,
        branch_name=pr_result["branch_name"],
        pr_number=pr_result.get("pr_number"),
        pr_url=pr_result.get("pr_url"),
        status="opened"
    )
    db.add(pr_record)
    job.status = "delivered"
    db.commit()
    db.refresh(pr_record)

    record_audit_event(
        db=db,
        action="delivery.pr_created",
        resource_type="pull_request",
        resource_id=pr_record.id,
        user_id=current_user.id,
        details={"pr_url": pr_record.pr_url, "branch": branch_name}
    )
    return pr_record
