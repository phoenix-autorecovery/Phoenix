import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.incident import Incident
from backend.app.models.repair import RepairJob, CandidatePatch, Approval
from backend.app.schemas.repair import ApprovalCreate, ApprovalResponse
from backend.app.core.security import get_current_user, require_roles
from backend.app.core.audit import record_audit_event
from backend.app.services.repair import RepairEngine

router = APIRouter(prefix="/approvals", tags=["Approvals & Human Gates"])

@router.get("", response_model=List[ApprovalResponse])
def list_approvals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Backfill any repair jobs in awaiting_approval that do not yet have a pending approval row
    pending_jobs = db.query(RepairJob).filter(RepairJob.status == "awaiting_approval").all()
    for pj in pending_jobs:
        existing = db.query(Approval).filter(Approval.repair_job_id == pj.id).first()
        if not existing and pj.patch_hash:
            latest_patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == pj.id).order_by(CandidatePatch.created_at.desc()).first()
            if latest_patch:
                db.add(Approval(
                    repair_job_id=pj.id,
                    candidate_patch_id=latest_patch.id,
                    user_id=current_user.id,
                    status="pending",
                    patch_hash=pj.patch_hash,
                    base_commit=pj.base_commit,
                    reviewer_notes="Candidate patch verified in isolated sandbox. Human cryptographic sign-off required."
                ))
    db.commit()

    # 2. Query approvals
    query = db.query(Approval).join(RepairJob).join(Project)
    if current_user.role not in ["admin", "reviewer", "auditor"]:
        query = query.filter(Project.user_id == current_user.id)
    
    approvals = query.order_by(
        # Show 'pending' first, then latest created
        (Approval.status != "pending"),
        Approval.created_at.desc()
    ).all()

    # Enrich response with project & incident metadata
    results = []
    for app in approvals:
        res = ApprovalResponse(
            id=app.id,
            repair_job_id=app.repair_job_id,
            candidate_patch_id=app.candidate_patch_id,
            user_id=app.user_id,
            status=app.status,
            patch_hash=app.patch_hash,
            base_commit=app.base_commit,
            reviewer_notes=app.reviewer_notes,
            decided_at=app.decided_at,
            created_at=app.created_at,
            project_id=app.repair_job.project_id if app.repair_job else None,
            project_name=app.repair_job.project.name if app.repair_job and app.repair_job.project else None,
            incident_id=app.repair_job.incident_id if app.repair_job else None,
            incident_title=app.repair_job.incident.title if app.repair_job and app.repair_job.incident else None,
            diff_summary=(
                db.query(CandidatePatch.diff_summary)
                .filter(CandidatePatch.id == app.candidate_patch_id)
                .scalar() or "Autonomous candidate repair"
            )
        )
        results.append(res)

    return results

@router.post("/{repair_id}/approve", response_model=ApprovalResponse)
def approve_repair(
    repair_id: str,
    req: ApprovalCreate,
    current_user: User = Depends(require_roles(["admin", "reviewer", "developer"])),
    db: Session = Depends(get_db)
):
    job = db.query(RepairJob).join(Project).filter(RepairJob.id == repair_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Repair job not found.")
    if job.project.user_id != current_user.id and current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == repair_id).order_by(CandidatePatch.created_at.desc()).first()
    if not patch:
        raise HTTPException(status_code=404, detail="No candidate patch exists for this repair job.")

    # Cryptographic binding check: verify submitted patch_hash matches exactly
    if req.patch_hash.strip().lower() != patch.patch_hash.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Integrity check failed: Submitted patch hash does not match candidate patch hash."
        )

    # Check target project fingerprint has not mutated
    if job.base_commit and job.base_commit != job.project.content_fingerprint:
        raise HTTPException(
            status_code=409,
            detail="Target project fingerprint has mutated since candidate patch was generated. Approval invalidated."
        )

    # Find existing pending approval or create new
    approval = db.query(Approval).filter(Approval.repair_job_id == job.id).first()
    if not approval:
        approval = Approval(
            repair_job_id=job.id,
            candidate_patch_id=patch.id,
            user_id=current_user.id,
            status="approved",
            patch_hash=patch.patch_hash,
            base_commit=job.base_commit,
            reviewer_notes=req.notes or "Approved by human reviewer.",
            decided_at=datetime.datetime.utcnow()
        )
        db.add(approval)
    else:
        approval.status = "approved"
        approval.decided_at = datetime.datetime.utcnow()
        approval.reviewer_notes = req.notes or "Approved by human reviewer."
        approval.user_id = current_user.id

    job.status = "approved"

    # Human sign-off complete: Now apply the fix directly to the target project workspace
    workspace_dir = Path(job.project.root_path)
    if workspace_dir.exists():
        RepairEngine.apply_patch_to_dir(workspace_dir, patch.patch_content)

    # Mark incident as resolved
    incident = db.query(Incident).filter(Incident.id == job.incident_id).first()
    if incident:
        incident.status = "resolved"

    db.commit()
    db.refresh(approval)

    record_audit_event(
        db=db,
        action="repair.approved",
        resource_type="approval",
        resource_id=approval.id,
        user_id=current_user.id,
        details={"patch_hash": patch.patch_hash, "reviewer": current_user.email}
    )

    return ApprovalResponse(
        id=approval.id,
        repair_job_id=approval.repair_job_id,
        candidate_patch_id=approval.candidate_patch_id,
        user_id=approval.user_id,
        status=approval.status,
        patch_hash=approval.patch_hash,
        base_commit=approval.base_commit,
        reviewer_notes=approval.reviewer_notes,
        decided_at=approval.decided_at,
        created_at=approval.created_at,
        project_id=job.project_id,
        project_name=job.project.name,
        incident_id=job.incident_id,
        incident_title=incident.title if incident else None,
        diff_summary=patch.diff_summary
    )

@router.post("/{repair_id}/reject", response_model=ApprovalResponse)
def reject_repair(
    repair_id: str,
    req: ApprovalCreate,
    current_user: User = Depends(require_roles(["admin", "reviewer", "developer"])),
    db: Session = Depends(get_db)
):
    job = db.query(RepairJob).join(Project).filter(RepairJob.id == repair_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Repair job not found.")
    if job.project.user_id != current_user.id and current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == repair_id).order_by(CandidatePatch.created_at.desc()).first()
    if not patch:
        raise HTTPException(status_code=404, detail="No candidate patch found.")

    approval = db.query(Approval).filter(Approval.repair_job_id == job.id).first()
    if not approval:
        approval = Approval(
            repair_job_id=job.id,
            candidate_patch_id=patch.id,
            user_id=current_user.id,
            status="rejected",
            patch_hash=patch.patch_hash,
            base_commit=job.base_commit,
            reviewer_notes=req.notes or "Rejected by human reviewer.",
            decided_at=datetime.datetime.utcnow()
        )
        db.add(approval)
    else:
        approval.status = "rejected"
        approval.decided_at = datetime.datetime.utcnow()
        approval.reviewer_notes = req.notes or "Rejected by human reviewer."
        approval.user_id = current_user.id

    job.status = "rejected"

    # Re-open incident for revised diagnosis/repair
    incident = db.query(Incident).filter(Incident.id == job.incident_id).first()
    if incident:
        incident.status = "diagnosed"

    db.commit()
    db.refresh(approval)

    record_audit_event(
        db=db,
        action="repair.rejected",
        resource_type="approval",
        resource_id=approval.id,
        user_id=current_user.id,
        details={"reason": req.notes}
    )

    return ApprovalResponse(
        id=approval.id,
        repair_job_id=approval.repair_job_id,
        candidate_patch_id=approval.candidate_patch_id,
        user_id=approval.user_id,
        status=approval.status,
        patch_hash=approval.patch_hash,
        base_commit=approval.base_commit,
        reviewer_notes=approval.reviewer_notes,
        decided_at=approval.decided_at,
        created_at=approval.created_at,
        project_id=job.project_id,
        project_name=job.project.name,
        incident_id=job.incident_id,
        incident_title=incident.title if incident else None,
        diff_summary=patch.diff_summary
    )
