"""
Autonomous Multi-Agent Runtime Orchestrator
Coordinates ProjectIntelligence, Diagnosis, Repair, Testing, Security, and Review agents
via a durable state machine with full execution telemetry.
"""
import asyncio
import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models.repair import RepairJob
from backend.app.models.incident import Incident
from backend.app.services.agents.base import AgentContext, AgentEvent
from backend.app.services.agents.intelligence_agent import ProjectIntelligenceAgent
from backend.app.services.agents.diagnosis_agent import DiagnosisAgent
from backend.app.services.agents.repair_agent import RepairAgent
from backend.app.services.agents.testing_agent import TestingAgent
from backend.app.services.agents.security_agent import SecurityAgent
from backend.app.services.agents.review_agent import ReviewAgent

logger = logging.getLogger("phoenix.agents.orchestrator")


class AutonomousAgentOrchestrator:
    """
    Central orchestrator executing multi-agent workflows with state tracking,
    rollback safeguards, and telemetry streaming.
    """
    _instance: Optional["AutonomousAgentOrchestrator"] = None
    _active_contexts: Dict[str, AgentContext] = {}

    def __init__(self):
        self.intelligence_agent = ProjectIntelligenceAgent()
        self.diagnosis_agent = DiagnosisAgent()
        self.repair_agent = RepairAgent()
        self.testing_agent = TestingAgent()
        self.security_agent = SecurityAgent()
        self.review_agent = ReviewAgent()

    @classmethod
    def get_instance(cls) -> "AutonomousAgentOrchestrator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_timeline(self, job_id: str) -> List[Dict[str, Any]]:
        """Retrieve real-time event timeline for an active or completed multi-agent job."""
        ctx = self._active_contexts.get(job_id)
        if not ctx:
            return []
        return [e.model_dump() for e in ctx.events]

    async def execute_repair_workflow(
        self,
        project_id: str,
        incident_id: str,
        model_name: str = "llama-3.1-70b-versatile",
        db_override: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-agent recovery workflow:
        Intelligence -> Diagnosis -> Repair -> Testing -> Security -> Review
        """
        db: Session = db_override if db_override is not None else SessionLocal()
        should_close_db = db_override is None
        job_id = str(uuid.uuid4())

        # Create RepairJob record in DB
        job = RepairJob(
            id=job_id,
            incident_id=incident_id,
            project_id=project_id,
            status="generating",
            repair_plan_json=json.dumps({"strategy": "multi_agent_autonomous_runtime", "model": model_name})
        )
        db.add(job)
        db.commit()

        context = AgentContext(
            project_id=project_id,
            incident_id=incident_id,
            job_id=job_id,
            model_name=model_name
        )
        self._active_contexts[job_id] = context

        context.log("Orchestrator", "workflow_init", f"Starting PHOENIX Multi-Agent Recovery Runtime (Job ID: {job_id[:8]})")

        try:
            # 1. Project Intelligence Agent
            context.log("Orchestrator", "stage_transition", "Dispatching Project Intelligence Agent...")
            intel_out = await self.intelligence_agent.run(context, db)
            context.state.update(intel_out)

            # 2. Diagnosis Agent
            context.log("Orchestrator", "stage_transition", "Dispatching Diagnosis Agent...")
            diag_out = await self.diagnosis_agent.run(context, db)
            context.state.update(diag_out)

            # 3. Repair Agent
            context.log("Orchestrator", "stage_transition", "Dispatching Code Repair Agent...")
            repair_out = await self.repair_agent.run(context, db)
            context.state.update(repair_out)

            # 4. Testing Agent
            context.log("Orchestrator", "stage_transition", "Dispatching Deterministic Sandbox Testing Agent...")
            test_out = await self.testing_agent.run(context, db)
            context.state.update(test_out)

            # 5. Security Agent
            context.log("Orchestrator", "stage_transition", "Dispatching Static Vulnerability & Security Agent...")
            sec_out = await self.security_agent.run(context, db)
            context.state.update(sec_out)

            # 6. Review Agent
            context.log("Orchestrator", "stage_transition", "Dispatching Review & Cryptographic Governance Agent...")
            review_out = await self.review_agent.run(context, db)
            context.state.update(review_out)

            # Finalize Status
            verdict = review_out.get("review_verdict")
            if verdict == "READY_FOR_APPROVAL":
                job.status = "awaiting_approval"
            elif verdict == "REJECTED_SECURITY_VETO":
                job.status = "rejected_security_veto"
            else:
                job.status = "failed_validation"

            job.updated_at = datetime.datetime.now(datetime.UTC)
            job.patch_hash = context.state.get("patch_hash")
            job.repair_plan_json = json.dumps({
                "strategy": "multi_agent_autonomous_runtime",
                "model": model_name,
                "verdict": verdict,
                "approval_id": review_out.get("approval_id"),
                "patch_id": context.state.get("patch_id"),
                "events_count": len(context.events)
            })
            db.commit()

            context.log("Orchestrator", "workflow_complete", f"Multi-Agent Workflow concluded: {verdict}", level="success")

            return {
                "job_id": job_id,
                "status": job.status,
                "verdict": verdict,
                "approval_id": review_out.get("approval_id"),
                "patch_id": context.state.get("patch_id"),
                "events": [e.model_dump() for e in context.events]
            }

        except Exception as e:
            logger.error(f"Error in multi-agent workflow for job {job_id}: {e}", exc_info=True)
            job.status = "failed"
            job.updated_at = datetime.datetime.now(datetime.UTC)
            db.commit()
            context.log("Orchestrator", "workflow_crash", f"Workflow execution halted: {str(e)}", level="error")
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
                "events": [e.model_dump() for e in context.events]
            }
        finally:
            if should_close_db:
                db.close()


agent_orchestrator = AutonomousAgentOrchestrator.get_instance()
