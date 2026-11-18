"""
Project Intelligence Agent
Maps repository architecture, AST topology, dependency manifests, and test suites.
"""
import logging
from pathlib import Path
from typing import Any, Dict
from backend.app.models.project import Project
from backend.app.services.agents.base import BaseAgent, AgentContext
from backend.app.services.intelligence import ProjectIntelligenceService

logger = logging.getLogger("phoenix.agents.intelligence")


class ProjectIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ProjectIntelligenceAgent",
            role="Codebase Architecture & Dependency Mapper"
        )

    async def run(self, context: AgentContext, db_session: Any) -> Dict[str, Any]:
        context.log(self.name, "analysis_start", f"Scanning repository AST topology for project '{context.project_id}'...")
        
        try:
            proj = db_session.query(Project).filter(Project.id == context.project_id).first()
            if not proj:
                raise ValueError(f"Project '{context.project_id}' not found.")
            
            workspace_dir = Path(proj.root_path)
            intel = ProjectIntelligenceService.analyze_workspace(workspace_dir)
            context.log(
                self.name,
                "analysis_complete",
                f"AST scan complete. Detected {intel.get('detected_language')} / {intel.get('detected_framework')}, test command: '{intel.get('test_commands')}'",
                level="success",
                data={"framework": intel.get("detected_framework"), "language": intel.get("detected_language")}
            )
            return {"intelligence": intel, "workspace_dir": str(workspace_dir)}
        except Exception as e:
            context.log(self.name, "analysis_error", f"Intelligence scan failed: {str(e)}", level="error")
            raise e
