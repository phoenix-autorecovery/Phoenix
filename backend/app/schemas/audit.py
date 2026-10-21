import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class AuditEventResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    correlation_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class DashboardMetrics(BaseModel):
    total_projects: int
    active_jobs: int
    open_incidents: int
    resolved_incidents: int
    pending_approvals: int
    recent_audits: List[AuditEventResponse] = []
