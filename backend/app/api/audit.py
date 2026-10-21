import json
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.incident import Incident
from backend.app.models.repair import RepairJob, Approval
from backend.app.models.audit import AuditEvent
from backend.app.schemas.audit import AuditEventResponse, DashboardMetrics
from backend.app.core.security import get_current_user

router = APIRouter(tags=["Audit & Monitoring"])

@router.get("/audit-events", response_model=List[AuditEventResponse])
def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(AuditEvent)
    if current_user.role not in ["admin", "auditor"]:
        query = query.filter(AuditEvent.user_id == current_user.id)
    events = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": ev.id,
            "user_id": ev.user_id,
            "action": ev.action,
            "resource_type": ev.resource_type,
            "resource_id": ev.resource_id,
            "correlation_id": ev.correlation_id,
            "ip_address": ev.ip_address,
            "details": json.loads(ev.details_json) if ev.details_json else None,
            "created_at": ev.created_at
        }
        for ev in events
    ]

@router.get("/monitoring/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_filter = (Project.user_id == current_user.id) if current_user.role != "admin" else True

    total_projects = db.query(Project).filter(user_filter).count()
    active_jobs = db.query(RepairJob).join(Project).filter(
        user_filter,
        RepairJob.status.in_(["queued", "generating", "validating", "awaiting_approval"])
    ).count()
    open_incidents = db.query(Incident).join(Project).filter(
        user_filter,
        Incident.status.in_(["detected", "diagnosing", "diagnosed", "repairing"])
    ).count()
    resolved_incidents = db.query(Incident).join(Project).filter(
        user_filter,
        Incident.status.in_(["resolved", "closed"])
    ).count()
    pending_approvals = db.query(Approval).join(RepairJob).join(Project).filter(
        user_filter,
        Approval.status == "pending"
    ).count()

    audit_query = db.query(AuditEvent)
    if current_user.role not in ["admin", "auditor"]:
        audit_query = audit_query.filter(AuditEvent.user_id == current_user.id)
    recent = audit_query.order_by(AuditEvent.created_at.desc()).limit(10).all()

    return {
        "total_projects": total_projects,
        "active_jobs": active_jobs,
        "open_incidents": open_incidents,
        "resolved_incidents": resolved_incidents,
        "pending_approvals": pending_approvals,
        "recent_audits": [
            {
                "id": ev.id,
                "user_id": ev.user_id,
                "action": ev.action,
                "resource_type": ev.resource_type,
                "resource_id": ev.resource_id,
                "correlation_id": ev.correlation_id,
                "ip_address": ev.ip_address,
                "details": json.loads(ev.details_json) if ev.details_json else None,
                "created_at": ev.created_at
            }
            for ev in recent
        ]
    }
