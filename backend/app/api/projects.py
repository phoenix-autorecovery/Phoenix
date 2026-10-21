import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.schemas.project import ProjectResponse, ProjectProfile
from backend.app.core.security import get_current_user
from backend.app.core.audit import record_audit_event
from backend.app.services.intelligence import ProjectIntelligenceService

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectResponse])
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "admin":
        return db.query(Project).order_by(Project.created_at.desc()).all()
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this project.")
    return project

@router.get("/{project_id}/profile", response_model=ProjectProfile)
def get_project_profile(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    
    workspace_dir = Path(project.root_path)
    if not workspace_dir.exists():
        raise HTTPException(status_code=404, detail="Project workspace directory is missing.")
    
    profile_data = ProjectIntelligenceService.analyze_workspace(workspace_dir)
    profile_data["name"] = project.name
    return profile_data

@router.get("/{project_id}/files")
def get_project_file_tree(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    workspace_dir = Path(project.root_path)
    if not workspace_dir.exists():
        return []

    file_list = []
    for root, dirs, files in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "__pycache__"}]
        for f in sorted(files):
            full_path = Path(root) / f
            rel = full_path.relative_to(workspace_dir).as_posix()
            file_list.append({
                "path": rel,
                "size_bytes": full_path.stat().st_size,
                "is_dir": False
            })
    return file_list

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    # Remove workspace directory from disk
    workspace_dir = Path(project.root_path)
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)

    db.delete(project)
    db.commit()

    record_audit_event(
        db=db,
        action="project.deleted",
        resource_type="project",
        resource_id=project_id,
        user_id=current_user.id
    )
    return None
