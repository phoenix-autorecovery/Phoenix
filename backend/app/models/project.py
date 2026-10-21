import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    input_type = Column(String(50), nullable=False)  # github, zip, local
    source_url = Column(String(1024), nullable=True)
    content_fingerprint = Column(String(64), nullable=True)  # SHA-256
    detected_language = Column(String(100), nullable=True)
    detected_framework = Column(String(100), nullable=True)
    root_path = Column(String(1024), nullable=False)
    health_status = Column(String(50), default="unknown", nullable=False)  # healthy, degraded, critical, unknown
    last_analysis_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", backref="projects")
    incidents = relationship("Incident", back_populates="project", cascade="all, delete-orphan")
    snapshots = relationship("ProjectSnapshot", back_populates="project", cascade="all, delete-orphan")

class ProjectSnapshot(Base):
    __tablename__ = "project_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    commit_sha = Column(String(64), nullable=True)
    file_count = Column(Integer, default=0, nullable=False)
    total_size_bytes = Column(Integer, default=0, nullable=False)
    manifest_json = Column(Text, nullable=False)  # JSON-encoded file manifest & tech profile
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="snapshots")
