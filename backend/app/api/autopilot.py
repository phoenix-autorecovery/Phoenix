import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.core.security import get_current_user
from backend.app.services.detector import WorkspaceDefectDetector
from backend.app.services.autopilot import AutoPilotService

logger = logging.getLogger("phoenix.api.autopilot")
router = APIRouter(tags=["Autonomous Auto-Pilot"])

class AutoPilotRequest(BaseModel):
    auto_apply: bool = True
    override_model: Optional[str] = None

class ModelSwitchRequest(BaseModel):
    model: str

@router.post("/projects/{project_id}/scan")
def scan_project_defects(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Runs automated defect detection across the project workspace
    (syntax errors, failing tests, crash logs).
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    workspace_dir = Path(project.root_path)
    defects = WorkspaceDefectDetector.scan_workspace_for_defects(workspace_dir)

    return {
        "project_id": project.id,
        "project_name": project.name,
        "defects_count": len(defects),
        "defects": defects,
        "status": "issues_detected" if defects else "healthy"
    }

@router.post("/projects/{project_id}/auto-pilot")
def trigger_autonomous_recovery(
    project_id: str,
    req: AutoPilotRequest = AutoPilotRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes complete autonomous self-healing loop:
    1. Detects errors & incidents automatically
    2. Runs Groq LLM diagnosis (powered by LLaMA 3.1 or Qwen)
    3. Generates candidate repair
    4. Deterministically validates in isolated sandbox
    5. Modifies workspace files directly and optionally delivers to GitHub
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    result = AutoPilotService.run_autonomous_recovery(
        project=project,
        db=db,
        current_user=current_user,
        auto_apply=req.auto_apply,
        override_model=req.override_model
    )
    return result

@router.get("/settings/models")
def get_supported_models(current_user: User = Depends(get_current_user)):
    """Returns available and active Groq LLM models (LLaMA 3.1, LLaMA 3.3, Qwen)."""
    return {
        "active_model": settings.GROQ_MODEL,
        "supported_models": settings.SUPPORTED_GROQ_MODELS,
        "llm_provider": settings.LLM_PROVIDER,
        "groq_api_key_configured": bool(settings.GROQ_API_KEY)
    }

@router.post("/settings/models")
def switch_active_model(
    req: ModelSwitchRequest,
    current_user: User = Depends(get_current_user)
):
    """Switches the active inference model across Groq LLaMA 3.1 and Qwen families."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can reconfigure default AI models.")

    if req.model not in settings.SUPPORTED_GROQ_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model '{req.model}'. Must be one of: {settings.SUPPORTED_GROQ_MODELS}"
        )

    settings.GROQ_MODEL = req.model
    logger.info(f"Active Groq LLM model switched to: {req.model}")
    return {
        "status": "success",
        "active_model": settings.GROQ_MODEL,
        "message": f"Active AI inference model switched to {req.model}."
    }
