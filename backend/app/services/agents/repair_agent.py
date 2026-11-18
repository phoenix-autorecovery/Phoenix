"""
Repair Agent
Synthesizes minimal unified git diff hunks to resolve root cause without extraneous modifications.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict
from backend.app.models.incident import Incident
from backend.app.models.project import Project
from backend.app.models.repair import CandidatePatch
from backend.app.services.agents.base import BaseAgent, AgentContext
from backend.app.services.repair import RepairEngine
from backend.app.services.validation import ValidationPipeline

logger = logging.getLogger("phoenix.agents.repair")


class RepairAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="RepairAgent",
            role="Code Synthesis & Unified Diff Patch Specialist"
        )

    async def run(self, context: AgentContext, db_session: Any) -> Dict[str, Any]:
        diag_data = context.state.get("diagnosis_data", {})
        
        inc = db_session.query(Incident).filter(Incident.id == context.incident_id).first()
        proj = db_session.query(Project).filter(Project.id == inc.project_id).first() if inc else None
        workspace_dir = Path(proj.root_path) if proj else Path(".")

        context.log(self.name, "synthesis_start", f"Synthesizing candidate patch hunk for incident '{context.incident_id}'...")
        
        try:
            repair_plan = RepairEngine.generate_candidate_repair(
                incident_title=inc.title if inc else "Incident",
                diagnosis_data=diag_data,
                workspace_dir=workspace_dir
            )

            patch_content = repair_plan.get("patch", "")
            patch_hash = ValidationPipeline.calculate_patch_hash(patch_content)

            candidate_patch = CandidatePatch(
                repair_job_id=context.job_id,
                patch_content=patch_content,
                diff_summary=repair_plan.get("intended_behavior", "Multi-agent autonomous repair"),
                files_modified_json=json.dumps(repair_plan.get("files_to_modify", [])),
                patch_hash=patch_hash
            )
            db_session.add(candidate_patch)
            db_session.commit()
            db_session.refresh(candidate_patch)

            context.log(
                self.name,
                "synthesis_complete",
                f"Candidate patch generated (SHA-256: {patch_hash[:12]}...). Files modified: {repair_plan.get('files_to_modify', [])}",
                level="success",
                data={
                    "patch_id": candidate_patch.id,
                    "patch_hash": patch_hash,
                    "diff_summary": candidate_patch.diff_summary,
                    "files_to_modify": repair_plan.get("files_to_modify", [])
                }
            )
            return {
                "patch_id": candidate_patch.id,
                "patch_content": patch_content,
                "patch_hash": patch_hash,
                "files_to_modify": repair_plan.get("files_to_modify", [])
            }
        except Exception as e:
            context.log(self.name, "synthesis_error", f"Patch synthesis failed: {str(e)}", level="error")
            raise e
