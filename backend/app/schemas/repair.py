import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class RepairJobCreate(BaseModel):
    incident_id: str

class CandidatePatchResponse(BaseModel):
    id: str
    repair_job_id: str
    patch_content: str
    diff_summary: Optional[str] = None
    files_modified: List[str] = []
    patch_hash: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ValidationRunResponse(BaseModel):
    id: str
    repair_job_id: str
    candidate_patch_id: str
    overall_status: str  # passed, failed, inconclusive
    exit_code: int
    duration_ms: int
    test_output: Optional[str] = None
    security_findings: List[Dict[str, Any]] = []
    validation_details: Optional[Dict[str, Any]] = None
    ran_at: datetime.datetime

    class Config:
        from_attributes = True

class ApprovalCreate(BaseModel):
    patch_hash: str
    notes: Optional[str] = None

class ApprovalResponse(BaseModel):
    id: str
    repair_job_id: str
    candidate_patch_id: str
    user_id: str
    status: str
    patch_hash: str
    base_commit: Optional[str] = None
    reviewer_notes: Optional[str] = None
    decided_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class PullRequestCreate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    target_branch: Optional[str] = "main"

class PullRequestResponse(BaseModel):
    id: str
    repair_job_id: str
    repository_url: str
    branch_name: str
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class RepairJobResponse(BaseModel):
    id: str
    incident_id: str
    project_id: str
    status: str
    retry_count: int
    max_retries: int
    patch_hash: Optional[str] = None
    base_commit: Optional[str] = None
    repair_plan: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    candidate_patches: List[CandidatePatchResponse] = []
    validation_runs: List[ValidationRunResponse] = []
    approvals: List[ApprovalResponse] = []
    pull_requests: List[PullRequestResponse] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
