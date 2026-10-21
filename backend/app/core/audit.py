import json
import logging
import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.audit import AuditEvent

logger = logging.getLogger("phoenix.audit")
logger.setLevel(logging.INFO)

def record_audit_event(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> AuditEvent:
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    details_str = json.dumps(details) if details else None
    
    audit = AuditEvent(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id,
        ip_address=ip_address,
        details_json=details_str
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    
    logger.info(
        f"[AUDIT] user={user_id} action={action} type={resource_type} "
        f"id={resource_id} corr={correlation_id}"
    )
    return audit
