"""
Diagnosis Agent
Investigates failure telemetry, stack traces, and formulates verifiable root cause hypotheses.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict
from backend.app.models.incident import Incident, Diagnosis
from backend.app.models.project import Project
from backend.app.services.agents.base import BaseAgent, AgentContext
from backend.app.services.diagnosis import DiagnosisEngine

logger = logging.getLogger("phoenix.agents.diagnosis")


class DiagnosisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="DiagnosisAgent",
            role="Root Cause Reasoner & Crash Telemetry Analyst"
        )

    async def run(self, context: AgentContext, db_session: Any) -> Dict[str, Any]:
        context.log(self.name, "diagnosis_start", f"Investigating crash telemetry for incident '{context.incident_id}' using model '{context.model_name}'...")
        
        try:
            inc = db_session.query(Incident).filter(Incident.id == context.incident_id).first()
            if not inc:
                raise ValueError(f"Incident '{context.incident_id}' not found.")

            proj = db_session.query(Project).filter(Project.id == inc.project_id).first()
            workspace_dir = Path(proj.root_path) if proj else Path(".")

            diag_res = DiagnosisEngine.diagnose_incident(
                title=inc.title,
                description=inc.description or "",
                stack_trace=inc.stack_trace or "",
                raw_log=inc.raw_log or "",
                workspace_dir=workspace_dir
            )

            diagnosis = Diagnosis(
                incident_id=inc.id,
                root_cause_hypothesis=diag_res.get("root_cause_hypothesis", "Autonomous multi-agent diagnosis"),
                confidence_score=diag_res.get("confidence_score", 0.9),
                evidence_json=json.dumps(diag_res.get("evidence", [])),
                relevant_files_json=json.dumps(diag_res.get("relevant_files", [])),
                suggested_action=diag_res.get("suggested_action", ""),
                is_repair_safe=diag_res.get("is_repair_safe", True),
                model_used=context.model_name
            )
            db_session.add(diagnosis)
            db_session.commit()
            db_session.refresh(diagnosis)

            context.log(
                self.name,
                "diagnosis_complete",
                f"Root cause identified: {diagnosis.root_cause_hypothesis[:120]}... [Confidence: {diagnosis.confidence_score:.2f}]",
                level="success",
                data={
                    "diagnosis_id": diagnosis.id,
                    "confidence_score": diagnosis.confidence_score,
                    "root_cause": diagnosis.root_cause_hypothesis,
                    "relevant_files": diag_res.get("relevant_files", [])
                }
            )
            return {"diagnosis_data": diag_res, "diagnosis_id": diagnosis.id}
        except Exception as e:
            context.log(self.name, "diagnosis_error", f"Diagnosis failed: {str(e)}", level="error")
            raise e
