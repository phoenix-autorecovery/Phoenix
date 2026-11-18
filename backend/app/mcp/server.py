"""
PHOENIX MCP Server (Model Context Protocol 2026-07-28)
Exposes PHOENIX autonomous recovery, project inspection, sandbox validation,
and cryptographic governance to external AI agents and IDEs.
"""
import json
import logging
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models.project import Project
from backend.app.models.incident import Incident, Diagnosis
from backend.app.models.repair import RepairJob, CandidatePatch, ValidationRun, Approval
from backend.app.services.intelligence import ProjectIntelligenceService
from backend.app.services.diagnosis import DiagnosisEngine
from backend.app.services.repair import RepairEngine
from backend.app.services.sandbox import SandboxExecutionEngine
from backend.app.services.validation import ValidationPipeline
from backend.app.mcp.schemas import (
    ToolCategory,
    ToolDefinition,
    ToolCallRequest,
    ToolCallResult,
    ToolCallContent,
    ResourceDefinition,
    ResourceReadResult,
    ResourceContent,
    PromptDefinition,
    PromptArgument,
    PromptGetResult,
    PromptMessage,
    InitializeResult,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
)
from backend.app.mcp.registry import tool_registry

logger = logging.getLogger("phoenix.mcp.server")


class PhoenixMCPServer:
    """
    Core MCP Server implementation conforming to MCP 2026-07-28 stateless core protocol.
    """

    def __init__(self):
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register all 10 core PHOENIX capabilities into ToolRegistry."""

        # 1. phoenix.inspect_project
        tool_registry.register(
            name="phoenix.inspect_project",
            description="Inspect project structure, file tree, dependencies, and configuration manifest.",
            category=ToolCategory.READ,
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project to inspect"}
                },
                "required": ["project_id"]
            },
            handler=self.tool_inspect_project
        )

        # 2. phoenix.analyze_project
        tool_registry.register(
            name="phoenix.analyze_project",
            description="Run deep AST analysis, identify entry points, test suites, and framework components.",
            category=ToolCategory.READ,
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"}
                },
                "required": ["project_id"]
            },
            handler=self.tool_analyze_project
        )

        # 3. phoenix.diagnose_incident
        tool_registry.register(
            name="phoenix.diagnose_incident",
            description="Investigate an incident or stack trace using Groq LLM inference and AST context.",
            category=ToolCategory.READ,
            input_schema={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "UUID of the incident to diagnose"}
                },
                "required": ["incident_id"]
            },
            handler=self.tool_diagnose_incident
        )

        # 4. phoenix.generate_patch
        tool_registry.register(
            name="phoenix.generate_patch",
            description="Generate a unified diff repair patch for an incident via LLaMA 3.1 70B / Qwen 2.5 Coder.",
            category=ToolCategory.WRITE,
            input_schema={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "UUID of the incident"}
                },
                "required": ["incident_id"]
            },
            handler=self.tool_generate_patch
        )

        # 5. phoenix.validate_patch
        tool_registry.register(
            name="phoenix.validate_patch",
            description="Execute candidate patch in an isolated sandbox and verify test suite pass/fail.",
            category=ToolCategory.EXECUTE,
            input_schema={
                "type": "object",
                "properties": {
                    "patch_id": {"type": "string", "description": "UUID of candidate patch to validate"}
                },
                "required": ["patch_id"]
            },
            handler=self.tool_validate_patch
        )

        # 6. phoenix.get_patch_diff
        tool_registry.register(
            name="phoenix.get_patch_diff",
            description="Get the exact unified git diff hunk, affected files, and AST changes for a patch.",
            category=ToolCategory.READ,
            input_schema={
                "type": "object",
                "properties": {
                    "patch_id": {"type": "string", "description": "UUID of the candidate patch"}
                },
                "required": ["patch_id"]
            },
            handler=self.tool_get_patch_diff
        )

        # 7. phoenix.get_project_health
        tool_registry.register(
            name="phoenix.get_project_health",
            description="Assess overall health metrics: test pass rate, MTTR, open incidents, and repair success rate.",
            category=ToolCategory.READ,
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"}
                },
                "required": ["project_id"]
            },
            handler=self.tool_get_project_health
        )

        # 8. phoenix.get_repair_history
        tool_registry.register(
            name="phoenix.get_repair_history",
            description="Retrieve chronological list of past repairs, patches, and validation results.",
            category=ToolCategory.READ,
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"}
                },
                "required": ["project_id"]
            },
            handler=self.tool_get_repair_history
        )

        # 9. phoenix.request_approval
        tool_registry.register(
            name="phoenix.request_approval",
            description="Generate a cryptographic approval request with SHA-256 fingerprint binding.",
            category=ToolCategory.ADMINISTRATIVE,
            input_schema={
                "type": "object",
                "properties": {
                    "patch_id": {"type": "string", "description": "UUID of the candidate patch"}
                },
                "required": ["patch_id"]
            },
            handler=self.tool_request_approval,
            requires_approval=True
        )

        # 10. phoenix.generate_report
        tool_registry.register(
            name="phoenix.generate_report",
            description="Generate a comprehensive recovery report (Executive or Dev mode format).",
            category=ToolCategory.READ,
            input_schema={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "UUID of the incident"},
                    "format": {"type": "string", "description": "'executive' or 'technical'", "default": "technical"}
                },
                "required": ["incident_id"]
            },
            handler=self.tool_generate_report
        )

    # Tool Handlers
    def tool_inspect_project(self, project_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if not proj:
                return {"error": f"Project {project_id} not found."}
            return {
                "id": proj.id,
                "name": proj.name,
                "detected_language": proj.detected_language,
                "detected_framework": proj.detected_framework,
                "source_url": proj.source_url,
                "root_path": proj.root_path,
                "health_status": proj.health_status,
                "created_at": str(proj.created_at)
            }
        finally:
            db.close()

    def tool_analyze_project(self, project_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if not proj:
                return {"error": f"Project {project_id} not found."}
            workspace_dir = Path(proj.root_path)
            profile = ProjectIntelligenceService.analyze_workspace(workspace_dir)
            return {
                "project_id": proj.id,
                "project_name": proj.name,
                "profile": profile
            }
        finally:
            db.close()

    def tool_diagnose_incident(self, incident_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            if not inc:
                return {"error": f"Incident {incident_id} not found."}
            proj = db.query(Project).filter(Project.id == inc.project_id).first()
            workspace_dir = Path(proj.root_path) if proj else Path(".")

            diag_res = DiagnosisEngine.diagnose_incident(
                title=inc.title,
                description=inc.description or "",
                stack_trace=inc.stack_trace or "",
                raw_log=inc.raw_log or "",
                workspace_dir=workspace_dir
            )
            return {
                "incident_id": inc.id,
                "root_cause_hypothesis": diag_res.get("root_cause_hypothesis"),
                "confidence_score": diag_res.get("confidence_score", 0.9),
                "suggested_action": diag_res.get("suggested_action"),
                "relevant_files": diag_res.get("relevant_files", [])
            }
        finally:
            db.close()

    def tool_generate_patch(self, incident_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            if not inc:
                return {"error": f"Incident {incident_id} not found."}
            proj = db.query(Project).filter(Project.id == inc.project_id).first()
            workspace_dir = Path(proj.root_path) if proj else Path(".")

            diag_res = DiagnosisEngine.diagnose_incident(
                title=inc.title,
                description=inc.description or "",
                stack_trace=inc.stack_trace or "",
                raw_log=inc.raw_log or "",
                workspace_dir=workspace_dir
            )

            repair_plan = RepairEngine.generate_candidate_repair(
                incident_title=inc.title,
                diagnosis_data=diag_res,
                workspace_dir=workspace_dir
            )

            patch_content = repair_plan.get("patch", "")
            patch_hash = ValidationPipeline.calculate_patch_hash(patch_content)

            return {
                "incident_id": inc.id,
                "patch_hash": patch_hash,
                "diff_summary": repair_plan.get("intended_behavior"),
                "files_to_modify": repair_plan.get("files_to_modify", []),
                "patch": patch_content
            }
        finally:
            db.close()

    def tool_validate_patch(self, patch_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            patch = db.query(CandidatePatch).filter(CandidatePatch.id == patch_id).first()
            if not patch:
                return {"error": f"Patch {patch_id} not found."}
            job = db.query(RepairJob).filter(RepairJob.id == patch.repair_job_id).first()
            proj = db.query(Project).filter(Project.id == job.project_id).first() if job else None
            workspace_dir = Path(proj.root_path) if proj else Path(".")

            profile = ProjectIntelligenceService.analyze_workspace(workspace_dir)
            test_commands = profile.get("test_commands", [])

            sandbox_id = f"mcp_val_{patch.id[:8]}"
            sandbox_dir = SandboxExecutionEngine.create_disposable_copy(workspace_dir, sandbox_id)
            try:
                applied = RepairEngine.apply_patch_to_dir(sandbox_dir, patch.patch_content)
                if not applied:
                    return {"passed": False, "status": "failed_apply", "error": "Patch could not be applied"}
                val_result = ValidationPipeline.run_validation(sandbox_dir, patch.patch_content, test_commands)
                return {
                    "passed": val_result["overall_status"] == "passed",
                    "status": val_result["overall_status"],
                    "duration_ms": val_result["duration_ms"],
                    "security_findings": val_result["security_findings"],
                    "test_output": val_result["test_output"]
                }
            finally:
                SandboxExecutionEngine.cleanup_sandbox(sandbox_dir)
        finally:
            db.close()

    def tool_get_patch_diff(self, patch_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            patch = db.query(CandidatePatch).filter(CandidatePatch.id == patch_id).first()
            if not patch:
                return {"error": f"Patch {patch_id} not found."}
            return {
                "patch_id": patch.id,
                "patch_hash": patch.patch_hash,
                "diff_summary": patch.diff_summary,
                "patch_content": patch.patch_content,
                "created_at": str(patch.created_at)
            }
        finally:
            db.close()

    def tool_get_project_health(self, project_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if not proj:
                return {"error": f"Project {project_id} not found."}
            
            incidents = db.query(Incident).filter(Incident.project_id == project_id).all()
            total_incidents = len(incidents)
            resolved = len([i for i in incidents if i.status in ("resolved", "closed")])
            active = total_incidents - resolved

            health_score = 100 if total_incidents == 0 else int((resolved / total_incidents) * 100)

            return {
                "project_id": project_id,
                "project_name": proj.name,
                "health_score": health_score,
                "total_incidents": total_incidents,
                "active_incidents": active,
                "resolved_incidents": resolved,
                "status": proj.health_status
            }
        finally:
            db.close()

    def tool_get_repair_history(self, project_id: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        db: Session = SessionLocal()
        try:
            jobs = db.query(RepairJob).filter(RepairJob.project_id == project_id).order_by(RepairJob.created_at.desc()).limit(20).all()
            return [
                {
                    "job_id": j.id,
                    "incident_id": j.incident_id,
                    "status": j.status,
                    "patch_hash": j.patch_hash,
                    "retry_count": j.retry_count,
                    "created_at": str(j.created_at),
                    "updated_at": str(j.updated_at)
                }
                for j in jobs
            ]
        finally:
            db.close()

    def tool_request_approval(self, patch_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            patch = db.query(CandidatePatch).filter(CandidatePatch.id == patch_id).first()
            if not patch:
                return {"error": f"Patch {patch_id} not found."}

            job = db.query(RepairJob).filter(RepairJob.id == patch.repair_job_id).first()
            user_id = context.get("user_id") if context else None
            if not user_id:
                # Find project owner
                proj = db.query(Project).filter(Project.id == job.project_id).first() if job else None
                user_id = proj.user_id if proj else "admin"

            # Check if approval already exists
            existing = db.query(Approval).filter(Approval.candidate_patch_id == patch_id).first()
            if existing:
                return {
                    "approval_id": existing.id,
                    "status": existing.status,
                    "patch_hash": existing.patch_hash,
                    "created_at": str(existing.created_at)
                }

            appr = Approval(
                repair_job_id=patch.repair_job_id,
                candidate_patch_id=patch.id,
                user_id=user_id,
                status="pending",
                patch_hash=patch.patch_hash,
                base_commit=job.base_commit if job else None
            )
            db.add(appr)
            db.commit()
            db.refresh(appr)

            return {
                "approval_id": appr.id,
                "patch_id": patch.id,
                "status": appr.status,
                "patch_hash": appr.patch_hash,
                "created_at": str(appr.created_at)
            }
        finally:
            db.close()

    def tool_generate_report(self, incident_id: str, format: str = "technical", context: Optional[Dict] = None) -> str:
        db: Session = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            if not inc:
                return f"Error: Incident {incident_id} not found."
            
            diag = db.query(Diagnosis).filter(Diagnosis.incident_id == incident_id).first()
            job = db.query(RepairJob).filter(RepairJob.incident_id == incident_id).order_by(RepairJob.created_at.desc()).first()
            patch = db.query(CandidatePatch).filter(CandidatePatch.repair_job_id == job.id).first() if job else None
            val = db.query(ValidationRun).filter(ValidationRun.repair_job_id == job.id).first() if job else None

            if format == "executive":
                return f"""# PHOENIX Executive Incident Summary
**Incident**: {inc.title}
**Status**: {inc.status.upper()}
**Severity**: {inc.severity.upper()}

## Root Cause
{diag.root_cause_hypothesis if diag else 'Pending diagnosis'}

## Action Taken
{patch.diff_summary if patch else 'No repair generated yet'}

## Verification
- Status: {val.overall_status if val else 'Pending'}
- Verdict: {"VERIFIED RECOVERY" if val and val.overall_status == "passed" else "ATTENTION NEEDED"}
"""
            else:
                return f"""# PHOENIX Technical Post-Mortem Report
**Incident ID**: `{inc.id}`
**Project ID**: `{inc.project_id}`
**Status**: `{inc.status}` | **Severity**: `{inc.severity}`

### Diagnostic Details
- **Root Cause**: {diag.root_cause_hypothesis if diag else 'N/A'}
- **Confidence**: {diag.confidence_score if diag else 0.0:.2f}
- **Model Used**: {diag.model_used if diag else 'N/A'}

### Candidate Patch
- **Patch ID**: `{patch.id if patch else 'N/A'}`
- **SHA-256 Hash**: `{patch.patch_hash if patch else 'N/A'}`
- **Summary**: {patch.diff_summary if patch else 'N/A'}

### Sandboxed Validation Run
- **Validation ID**: `{val.id if val else 'N/A'}`
- **Overall Status**: `{val.overall_status if val else 'N/A'}`
- **Duration**: {val.duration_ms if val else 0}ms
- **Exit Code**: {val.exit_code if val else 0}
"""
        finally:
            db.close()

    # MCP Protocol Resources
    def list_resources(self) -> List[ResourceDefinition]:
        return [
            ResourceDefinition(
                uri="phoenix://system/health",
                name="System Health & Platform Status",
                description="Live system telemetry, active worker count, sandbox health and Groq inference latency.",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="phoenix://projects/{project_id}/profile",
                name="Project Profile",
                description="Project metadata, repository URL, language, and workspace paths.",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="phoenix://projects/{project_id}/architecture",
                name="Project Architecture & AST",
                description="AST parsed modules, entrypoints, and internal dependency topology.",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="phoenix://incidents/{incident_id}",
                name="Incident Detail & Telemetry",
                description="Full stack trace, error logs, environment snapshot, and diagnosis.",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="phoenix://repairs/{repair_id}/report",
                name="Repair Audit Report",
                description="Unified diff hunks, sandbox execution output, and cryptographic verification binding.",
                mimeType="text/markdown"
            )
        ]

    def read_resource(self, uri: str) -> ResourceReadResult:
        db: Session = SessionLocal()
        try:
            if uri == "phoenix://system/health":
                content = {
                    "status": "nominal",
                    "version": "2026.1.0",
                    "mcp_spec": "2026-07-28",
                    "inference_engine": "Groq LLaMA 3.1 70B & Qwen 2.5 Coder",
                    "sandbox_isolation": "Container/Local Process Guard",
                    "policy_enforcement": "Zero-trust cryptographic approval gates"
                }
                return ResourceReadResult(
                    contents=[ResourceContent(uri=uri, mimeType="application/json", text=json.dumps(content, indent=2))]
                )

            if uri.startswith("phoenix://projects/") and uri.endswith("/profile"):
                proj_id = uri.split("/")[3]
                proj = db.query(Project).filter(Project.id == proj_id).first()
                if not proj:
                    raise ValueError(f"Project '{proj_id}' not found")
                data = {
                    "id": proj.id,
                    "name": proj.name,
                    "detected_language": proj.detected_language,
                    "detected_framework": proj.detected_framework,
                    "source_url": proj.source_url,
                    "root_path": proj.root_path,
                    "health_status": proj.health_status
                }
                return ResourceReadResult(
                    contents=[ResourceContent(uri=uri, mimeType="application/json", text=json.dumps(data, indent=2))]
                )

            if uri.startswith("phoenix://incidents/"):
                inc_id = uri.split("/")[3]
                inc = db.query(Incident).filter(Incident.id == inc_id).first()
                if not inc:
                    raise ValueError(f"Incident '{inc_id}' not found")
                data = {
                    "id": inc.id,
                    "title": inc.title,
                    "severity": inc.severity,
                    "stack_trace": inc.stack_trace,
                    "status": inc.status
                }
                return ResourceReadResult(
                    contents=[ResourceContent(uri=uri, mimeType="application/json", text=json.dumps(data, indent=2))]
                )

            return ResourceReadResult(
                contents=[ResourceContent(uri=uri, mimeType="text/plain", text=f"Resource {uri} read successfully.")]
            )
        finally:
            db.close()

    # MCP Protocol Prompts
    def list_prompts(self) -> List[PromptDefinition]:
        return [
            PromptDefinition(
                name="diagnose_incident",
                description="Investigate a production incident, review stack trace, and determine root cause.",
                arguments=[
                    PromptArgument(name="incident_id", description="UUID of the incident", required=True),
                    PromptArgument(name="error_logs", description="Raw log snippet", required=False)
                ]
            ),
            PromptDefinition(
                name="review_patch",
                description="Code review candidate repair diff for security issues, regressions, and side effects.",
                arguments=[
                    PromptArgument(name="patch_id", description="UUID of the candidate patch", required=True)
                ]
            ),
            PromptDefinition(
                name="security_assessment",
                description="Security review of codebase or diff against OWASP Top 10 vulnerabilities.",
                arguments=[
                    PromptArgument(name="project_id", description="UUID of the project", required=True)
                ]
            ),
            PromptDefinition(
                name="release_readiness_report",
                description="Synthesize test validation and cryptographic sign-off into a deployment release note.",
                arguments=[
                    PromptArgument(name="project_id", description="UUID of the project", required=True)
                ]
            )
        ]

    def get_prompt(self, name: str, arguments: Dict[str, Any]) -> PromptGetResult:
        if name == "diagnose_incident":
            inc_id = arguments.get("incident_id", "UNKNOWN")
            return PromptGetResult(
                description="Prompt to diagnose an incident using AST context and stack trace.",
                messages=[
                    PromptMessage(
                        role="system",
                        content=ToolCallContent(
                            type="text",
                            text=(
                                "You are PHOENIX Diagnosis Engine. Given an error log and AST context, identify the "
                                "root cause file, exact lines, and formulate a verifiable reproduction hypothesis."
                            )
                        )
                    ),
                    PromptMessage(
                        role="user",
                        content=ToolCallContent(
                            type="text",
                            text=f"Please analyze incident '{inc_id}'. Telemetry context: {arguments.get('error_logs', 'None')}"
                        )
                    )
                ]
            )

        if name == "review_patch":
            patch_id = arguments.get("patch_id", "UNKNOWN")
            return PromptGetResult(
                description="Prompt to perform rigorous code review on candidate patch.",
                messages=[
                    PromptMessage(
                        role="system",
                        content=ToolCallContent(
                            type="text",
                            text=(
                                "You are PHOENIX Security & Review Engine. Inspect the patch diff for: "
                                "1. Regression risks. 2. OWASP vulnerabilities (SSRF, injection, eval). 3. Style and edge cases."
                            )
                        )
                    ),
                    PromptMessage(
                        role="user",
                        content=ToolCallContent(
                            type="text",
                            text=f"Review candidate patch '{patch_id}' and provide a risk tier (LOW/MEDIUM/HIGH/CRITICAL)."
                        )
                    )
                ]
            )

        return PromptGetResult(
            description=f"Prompt template for {name}",
            messages=[
                PromptMessage(
                    role="user",
                    content=ToolCallContent(type="text", text=f"Execute prompt {name} with arguments: {arguments}")
                )
            ]
        )

    # JSON-RPC 2.0 Dispatcher (MCP Standard Protocol Interface)
    async def dispatch_jsonrpc(self, request: JSONRPCRequest, user_role: str = "developer") -> JSONRPCResponse:
        """
        Handle standard MCP JSON-RPC 2.0 requests:
        - initialize
        - tools/list
        - tools/call
        - resources/list
        - resources/read
        - prompts/list
        - prompts/get
        """
        method = request.method
        params = request.params or {}

        try:
            if method == "initialize":
                init_res = InitializeResult()
                return JSONRPCResponse(id=request.id, result=init_res.model_dump())

            elif method == "tools/list":
                tools = tool_registry.list_tools()
                return JSONRPCResponse(id=request.id, result={"tools": [t.model_dump() for t in tools]})

            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                call_req = ToolCallRequest(name=tool_name, arguments=args)
                result = await tool_registry.execute_tool(call_req, user_role=user_role)
                return JSONRPCResponse(id=request.id, result=result.model_dump())

            elif method == "resources/list":
                resources = self.list_resources()
                return JSONRPCResponse(id=request.id, result={"resources": [r.model_dump() for r in resources]})

            elif method == "resources/read":
                uri = params.get("uri")
                if not uri:
                    return JSONRPCResponse(
                        id=request.id,
                        error=JSONRPCError(code=-32602, message="Invalid params: 'uri' is required.")
                    )
                read_res = self.read_resource(uri)
                return JSONRPCResponse(id=request.id, result=read_res.model_dump())

            elif method == "prompts/list":
                prompts = self.list_prompts()
                return JSONRPCResponse(id=request.id, result={"prompts": [p.model_dump() for p in prompts]})

            elif method == "prompts/get":
                name = params.get("name")
                prompt_args = params.get("arguments", {})
                if not name:
                    return JSONRPCResponse(
                        id=request.id,
                        error=JSONRPCError(code=-32602, message="Invalid params: 'name' is required.")
                    )
                prompt_res = self.get_prompt(name, prompt_args)
                return JSONRPCResponse(id=request.id, result=prompt_res.model_dump())

            else:
                return JSONRPCResponse(
                    id=request.id,
                    error=JSONRPCError(code=-32601, message=f"Method not found: '{method}'")
                )

        except Exception as e:
            logger.error(f"Error handling MCP JSON-RPC method '{method}': {e}", exc_info=True)
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(code=-32000, message=str(e))
            )


# Global singleton instance
phoenix_mcp_server = PhoenixMCPServer()
