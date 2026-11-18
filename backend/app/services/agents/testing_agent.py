"""
Testing Agent
Applies candidate patch in isolated sandbox and executes deterministic test validation.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict
from backend.app.models.project import Project
from backend.app.models.repair import ValidationRun
from backend.app.services.agents.base import BaseAgent, AgentContext
from backend.app.services.sandbox import SandboxExecutionEngine
from backend.app.services.repair import RepairEngine
from backend.app.services.validation import ValidationPipeline
from backend.app.services.intelligence import ProjectIntelligenceService

logger = logging.getLogger("phoenix.agents.testing")


class TestingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="TestingAgent",
            role="Deterministic Sandbox Execution & Test Validator"
        )

    async def run(self, context: AgentContext, db_session: Any) -> Dict[str, Any]:
        patch_id = context.state.get("patch_id")
        patch_content = context.state.get("patch_content", "")
        if not patch_id:
            raise ValueError("Cannot run TestingAgent without prior patch_id in context.")

        proj = db_session.query(Project).filter(Project.id == context.project_id).first()
        workspace_dir = Path(proj.root_path) if proj else Path(".")

        profile = ProjectIntelligenceService.analyze_workspace(workspace_dir)
        test_commands = profile.get("test_commands", [])

        context.log(self.name, "sandbox_launch", f"Spinning up isolated disposable sandbox for patch '{patch_id[:8]}'...")
        
        sandbox_id = f"agent_val_{context.job_id[:8]}"
        sandbox_dir = SandboxExecutionEngine.create_disposable_copy(workspace_dir, sandbox_id)
        try:
            applied = RepairEngine.apply_patch_to_dir(sandbox_dir, patch_content)
            if not applied:
                context.log(self.name, "sandbox_apply_failed", "Patch hunk could not be applied cleanly to sandbox.", level="error")
                return {"validation_passed": False, "status": "failed_apply"}

            val_result = ValidationPipeline.run_validation(sandbox_dir, patch_content, test_commands)
            
            val_run = ValidationRun(
                repair_job_id=context.job_id,
                candidate_patch_id=patch_id,
                overall_status=val_result["overall_status"],
                exit_code=val_result.get("exit_code", 0),
                duration_ms=val_result["duration_ms"],
                test_output=val_result["test_output"],
                security_findings_json=json.dumps(val_result["security_findings"]),
                validation_details_json=json.dumps(val_result.get("commands_executed", []))
            )
            db_session.add(val_run)
            db_session.commit()
            db_session.refresh(val_run)

            status_level = "success" if val_result["overall_status"] == "passed" else "error"
            context.log(
                self.name,
                "validation_finished",
                f"Validation finished in {val_result['duration_ms']}ms with status '{val_result['overall_status']}'.",
                level=status_level,
                data={
                    "validation_id": val_run.id,
                    "overall_status": val_result["overall_status"],
                    "passed": val_result["overall_status"] == "passed",
                    "duration_ms": val_result["duration_ms"]
                }
            )
            return {
                "validation_run_id": val_run.id,
                "validation_passed": val_result["overall_status"] == "passed",
                "val_result": val_result
            }
        finally:
            SandboxExecutionEngine.cleanup_sandbox(sandbox_dir)
