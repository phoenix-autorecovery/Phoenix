import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.repair import RepairJob, CandidatePatch, Approval
from backend.app.schemas.repair import ApprovalCreate, ApprovalResponse
from backend.app.core.security import get_current_user, require_roles
from backend.app.core.audit import record_audit_event

router = APIRouter(prefix="/approvals", tags=["Approvals & Human Gates"])

@router.get("", response_model=List[ApprovalResponse])
def list_approvals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Approval).join(RepairJob).join(Project)
    if current_user.role not in ["admin", "reviewer"]:
        query = query.filter(Project.user_id == current_user.id)
    return query.order_by(Approval.created_at.desc()).all()

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

    approval = Approval(
        repair_job_id=job.id,
        candidate_patch_id=patch.id,
        user_id=current_user.id,
        status="approved",
        patch_hash=patch.patch_hash,
        base_commit=job.base_commit,
        reviewer_notes=req.notes,
        decided_at=datetime.datetime.utcnow()
    )
    db.add(approval)
    job.status = "approved"
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
    return approval

@router.post("/{repair_id}/reject", response_model=ApprovalResponse)
def reject_repair(
    repair_id: str,
    req: ApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(RepairJob).join(Project).filter(RepairJob.id == repair_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Repair job not found.")
    
    patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == repair_id).order_by(CandidatePatch.created_at.desc()).first()
    if not patch:
        raise HTTPException(status_code=404, detail="No candidate patch found.")

    approval = Approval(
        repair_job_id=job.id,
        candidate_patch_id=patch.id,
        user_id=current_user.id,
        status="rejected",
        patch_hash=patch.patch_hash,
        base_commit=job.base_commit,
        reviewer_notes=req.notes,
        decided_at=datetime.datetime.utcnow()
    )
    db.add(approval)
    job.status = "rejected"
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
    return approval
