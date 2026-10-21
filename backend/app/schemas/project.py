import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    input_type: str  # github, zip, local
    source_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class GitHubImportRequest(BaseModel):
    repository_url: str
    branch: Optional[str] = None

class LocalFolderManifestRequest(BaseModel):
    name: str
    project_root_name: str
    files: List[Dict[str, Any]]  # relative_path, content_b64 or text

class ProjectProfile(BaseModel):
    name: str
    detected_language: Optional[str] = None
    detected_framework: Optional[str] = None
    dependency_files: List[str] = []
    test_commands: List[str] = []
    lint_commands: List[str] = []
    file_count: int = 0
    total_size_bytes: int = 0
    health_status: str = "unknown"
    risks_identified: List[str] = []

class ProjectResponse(ProjectBase):
    id: str
    user_id: str
    content_fingerprint: Optional[str] = None
    detected_language: Optional[str] = None
    detected_framework: Optional[str] = None
    root_path: str
    health_status: str
    last_analysis_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
