import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class IncidentCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    raw_log: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: str = "high"

class DiagnosisResponse(BaseModel):
    id: str
    incident_id: str
    root_cause_hypothesis: str
    confidence_score: float
    evidence: List[Dict[str, Any]] = []
    relevant_files: List[Dict[str, Any]] = []
    suggested_action: Optional[str] = None
    is_repair_safe: bool = True
    model_used: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class IncidentResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    raw_log: Optional[str] = None
    stack_trace: Optional[str] = None
    error_signature: Optional[str] = None
    severity: str
    status: str
    diagnoses: List[DiagnosisResponse] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
