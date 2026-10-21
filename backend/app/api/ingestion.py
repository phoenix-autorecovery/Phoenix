import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project, ProjectSnapshot
from backend.app.schemas.project import ProjectResponse, GitHubImportRequest, LocalFolderManifestRequest
from backend.app.core.security import get_current_user
from backend.app.core.audit import record_audit_event
from backend.app.services.ingestion import IngestionService
from backend.app.services.intelligence import ProjectIntelligenceService

router = APIRouter(prefix="/ingestion", tags=["Project Ingestion"])

@router.post("/zip", response_model=ProjectResponse)
async def ingest_zip(
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project_id = str(uuid.uuid4())
    target_workspace = settings.WORKSPACES_DIR / project_id
    
    content = await file.read()
    ingest_result = IngestionService.extract_zip(content, target_workspace)
    intelligence = ProjectIntelligenceService.analyze_workspace(target_workspace)

    project = Project(
        id=project_id,
        user_id=current_user.id,
        name=name,
        description=description,
        input_type="zip",
        content_fingerprint=ingest_result["fingerprint"],
        detected_language=intelligence["detected_language"],
        detected_framework=intelligence["detected_framework"],
        root_path=str(target_workspace),
        health_status=intelligence["health_status"]
    )
    db.add(project)

    snapshot = ProjectSnapshot(
        project_id=project.id,
        file_count=ingest_result["file_count"],
        total_size_bytes=ingest_result["total_size"],
        manifest_json=str(intelligence)
    )
    db.add(snapshot)
    db.commit()
    db.refresh(project)

    record_audit_event(
        db=db,
        action="project.ingest.zip",
        resource_type="project",
        resource_id=project.id,
        user_id=current_user.id,
        details={"name": name, "file_count": ingest_result["file_count"]}
    )
    return project

@router.post("/github", response_model=ProjectResponse)
def ingest_github(
    req: GitHubImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project_id = str(uuid.uuid4())
    target_workspace = settings.WORKSPACES_DIR / project_id
    
    ingest_result = IngestionService.clone_github_repo(req.repository_url, target_workspace, branch=req.branch)
    intelligence = ProjectIntelligenceService.analyze_workspace(target_workspace)

    repo_name = req.repository_url.rstrip("/").split("/")[-1].replace(".git", "")
    project = Project(
        id=project_id,
        user_id=current_user.id,
        name=repo_name,
        description=f"Imported from {req.repository_url}",
        input_type="github",
        source_url=req.repository_url,
        content_fingerprint=ingest_result["fingerprint"],
        detected_language=intelligence["detected_language"],
        detected_framework=intelligence["detected_framework"],
        root_path=str(target_workspace),
        health_status=intelligence["health_status"]
    )
    db.add(project)

    snapshot = ProjectSnapshot(
        project_id=project.id,
        commit_sha=ingest_result.get("commit_sha"),
        file_count=ingest_result["file_count"],
        total_size_bytes=ingest_result["total_size"],
        manifest_json=str(intelligence)
    )
    db.add(snapshot)
    db.commit()
    db.refresh(project)

    record_audit_event(
        db=db,
        action="project.ingest.github",
        resource_type="project",
        resource_id=project.id,
        user_id=current_user.id,
        details={"repo": req.repository_url, "commit": ingest_result.get("commit_sha")}
    )
    return project

@router.post("/local", response_model=ProjectResponse)
def ingest_local_manifest(
    req: LocalFolderManifestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project_id = str(uuid.uuid4())
    target_workspace = settings.WORKSPACES_DIR / project_id
    target_workspace.mkdir(parents=True, exist_ok=True)

    for item in req.files:
        rel_path = item.get("path")
        text_content = item.get("content", "")
        # Protect against path traversal
        dest_file = (target_workspace / rel_path).resolve()
        if not str(dest_file).startswith(str(target_workspace.resolve())):
            raise HTTPException(status_code=400, detail=f"Path traversal detected: {rel_path}")
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_text(text_content, encoding="utf-8")

    fingerprint, count, size = IngestionService.calculate_dir_fingerprint(target_workspace)
    intelligence = ProjectIntelligenceService.analyze_workspace(target_workspace)

    project = Project(
        id=project_id,
        user_id=current_user.id,
        name=req.name,
        description="Synchronized via PHOENIX companion CLI",
        input_type="local",
        content_fingerprint=fingerprint,
        detected_language=intelligence["detected_language"],
        detected_framework=intelligence["detected_framework"],
        root_path=str(target_workspace),
        health_status=intelligence["health_status"]
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    record_audit_event(
        db=db,
        action="project.ingest.local",
        resource_type="project",
        resource_id=project.id,
        user_id=current_user.id,
        details={"name": req.name, "files_count": count}
    )
    return project
