import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    raw_log = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    error_signature = Column(String(255), nullable=True)
    severity = Column(String(50), default="high", nullable=False)  # critical, high, medium, low
    status = Column(String(50), default="detected", nullable=False)  # detected, diagnosing, diagnosed, repairing, resolved, closed
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="incidents")
    diagnoses = relationship("Diagnosis", back_populates="incident", cascade="all, delete-orphan")
    repairs = relationship("RepairJob", back_populates="incident", cascade="all, delete-orphan")

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    root_cause_hypothesis = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.0, nullable=False)
    evidence_json = Column(Text, nullable=True)  # JSON-encoded array of evidence items
    relevant_files_json = Column(Text, nullable=True)  # JSON-encoded file paths & line numbers
    suggested_action = Column(Text, nullable=True)
    is_repair_safe = Column(Boolean, default=True, nullable=False)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    incident = relationship("Incident", back_populates="diagnoses")
