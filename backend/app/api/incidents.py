import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.incident import Incident, Diagnosis
from backend.app.schemas.incident import IncidentCreate, IncidentResponse, DiagnosisResponse
from backend.app.core.security import get_current_user
from backend.app.core.audit import record_audit_event
from backend.app.services.diagnosis import DiagnosisEngine

router = APIRouter(prefix="/incidents", tags=["Incidents & Diagnosis"])

@router.post("", response_model=IncidentResponse)
def create_incident(inc_in: IncidentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == inc_in.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    error_signature = DiagnosisEngine.extract_error_signature(inc_in.stack_trace, inc_in.raw_log)

    incident = Incident(
        project_id=project.id,
        title=inc_in.title,
        description=inc_in.description,
        raw_log=inc_in.raw_log,
        stack_trace=inc_in.stack_trace,
        error_signature=error_signature,
        severity=inc_in.severity,
        status="detected"
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    record_audit_event(
        db=db,
        action="incident.created",
        resource_type="incident",
        resource_id=incident.id,
        user_id=current_user.id,
        details={"title": incident.title, "signature": error_signature}
    )
    return incident

@router.get("", response_model=List[IncidentResponse])
def list_incidents(project_id: str = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Incident).join(Project)
    if project_id:
        query = query.filter(Incident.project_id == project_id)
    if current_user.role != "admin":
        query = query.filter(Project.user_id == current_user.id)
    return query.order_by(Incident.created_at.desc()).all()

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    incident = db.query(Incident).join(Project).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if incident.project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    return incident

@router.post("/{incident_id}/diagnose", response_model=DiagnosisResponse)
def trigger_diagnosis(incident_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    incident = db.query(Incident).join(Project).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if incident.project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    incident.status = "diagnosing"
    db.commit()

    workspace_dir = Path(incident.project.root_path)
    res = DiagnosisEngine.diagnose_incident(
        title=incident.title,
        description=incident.description or "",
        stack_trace=incident.stack_trace or "",
        raw_log=incident.raw_log or "",
        workspace_dir=workspace_dir
    )

    diag_dict = res["diagnosis"]
    diagnosis = Diagnosis(
        incident_id=incident.id,
        root_cause_hypothesis=diag_dict.get("root_cause_hypothesis", "Unknown"),
        confidence_score=float(diag_dict.get("confidence_score", 0.0)),
        evidence_json=json.dumps(diag_dict.get("evidence", [])),
        relevant_files_json=json.dumps(diag_dict.get("relevant_files", [])),
        suggested_action=diag_dict.get("suggested_action", ""),
        is_repair_safe=bool(diag_dict.get("is_repair_safe", True)),
        model_used=res["model_used"]
    )
    db.add(diagnosis)
    incident.status = "diagnosed"
    db.commit()
    db.refresh(diagnosis)

    record_audit_event(
        db=db,
        action="incident.diagnosed",
        resource_type="diagnosis",
        resource_id=diagnosis.id,
        user_id=current_user.id,
        details={"confidence": diagnosis.confidence_score, "safe": diagnosis.is_repair_safe}
    )

    return {
        "id": diagnosis.id,
        "incident_id": diagnosis.incident_id,
        "root_cause_hypothesis": diagnosis.root_cause_hypothesis,
        "confidence_score": diagnosis.confidence_score,
        "evidence": json.loads(diagnosis.evidence_json or "[]"),
        "relevant_files": json.loads(diagnosis.relevant_files_json or "[]"),
        "suggested_action": diagnosis.suggested_action,
        "is_repair_safe": diagnosis.is_repair_safe,
        "model_used": diagnosis.model_used,
        "created_at": diagnosis.created_at
    }
