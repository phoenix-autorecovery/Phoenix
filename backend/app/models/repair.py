import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from backend.app.database import Base

class RepairJob(Base):
    __tablename__ = "repair_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="queued", nullable=False)  # queued, generating, validating, awaiting_approval, approved, rejected, delivered, failed
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    patch_hash = Column(String(64), nullable=True)  # SHA-256 of candidate patch
    base_commit = Column(String(64), nullable=True)
    repair_plan_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    incident = relationship("Incident", back_populates="repairs")
    project = relationship("Project")
    candidate_patches = relationship("CandidatePatch", back_populates="repair_job", cascade="all, delete-orphan")
    validation_runs = relationship("ValidationRun", back_populates="repair_job", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="repair_job", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequestRecord", back_populates="repair_job", cascade="all, delete-orphan")

class CandidatePatch(Base):
    __tablename__ = "candidate_patches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repair_job_id = Column(String(36), ForeignKey("repair_jobs.id", ondelete="CASCADE"), nullable=False)
    patch_content = Column(Text, nullable=False)  # Unified diff format
    diff_summary = Column(Text, nullable=True)
    files_modified_json = Column(Text, nullable=True)  # List of modified file paths
    patch_hash = Column(String(64), nullable=False)  # SHA-256 hash of patch_content
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    repair_job = relationship("RepairJob", back_populates="candidate_patches")
    validation_runs = relationship("ValidationRun", back_populates="candidate_patch")

class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repair_job_id = Column(String(36), ForeignKey("repair_jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_patch_id = Column(String(36), ForeignKey("candidate_patches.id", ondelete="CASCADE"), nullable=False)
    overall_status = Column(String(50), nullable=False)  # passed, failed, inconclusive, skipped
    exit_code = Column(Integer, default=0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)
    test_output = Column(Text, nullable=True)
    security_findings_json = Column(Text, nullable=True)  # JSON-encoded array of findings
    validation_details_json = Column(Text, nullable=True)  # Commands executed, tool versions
    ran_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    repair_job = relationship("RepairJob", back_populates="validation_runs")
    candidate_patch = relationship("CandidatePatch", back_populates="validation_runs")

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repair_job_id = Column(String(36), ForeignKey("repair_jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_patch_id = Column(String(36), ForeignKey("candidate_patches.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected, invalidated
    patch_hash = Column(String(64), nullable=False)  # Bound to candidate patch hash
    base_commit = Column(String(64), nullable=True)  # Bound to base commit/fingerprint
    reviewer_notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    repair_job = relationship("RepairJob", back_populates="approvals")
    user = relationship("User")

class PullRequestRecord(Base):
    __tablename__ = "pull_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repair_job_id = Column(String(36), ForeignKey("repair_jobs.id", ondelete="CASCADE"), nullable=False)
    repository_url = Column(String(1024), nullable=False)
    branch_name = Column(String(255), nullable=False)
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(1024), nullable=True)
    status = Column(String(50), default="created", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    repair_job = relationship("RepairJob", back_populates="pull_requests")
