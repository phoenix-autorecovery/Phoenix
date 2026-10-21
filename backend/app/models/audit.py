import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from backend.app.database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)  # project.import, diagnosis.create, repair.generate, patch.approve, etc.
    resource_type = Column(String(100), nullable=False)  # project, incident, repair_job, approval, system
    resource_id = Column(String(100), nullable=True)
    correlation_id = Column(String(64), nullable=True)
    ip_address = Column(String(50), nullable=True)
    details_json = Column(Text, nullable=True)  # Context payload
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    is_secret = Column(String(10), default="false", nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
