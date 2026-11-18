"""
PHOENIX MCP Client
Connects PHOENIX to external MCP servers (GitHub, Filesystem, Database, Documentation, etc.)
with schema validation, least-privilege permission gating, and audit logging.
"""
import asyncio
import httpx
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.mcp.schemas import ToolCategory, ToolDefinition, ToolCallRequest, ToolCallResult, ToolCallContent
from backend.app.mcp.registry import tool_registry

logger = logging.getLogger("phoenix.mcp.client")


class ExternalMCPServerConfig(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    command: Optional[str] = None
    auth_token: Optional[str] = None
    allowed_categories: List[ToolCategory] = Field(
        default_factory=lambda: [ToolCategory.READ, ToolCategory.WRITE]
    )
    timeout_seconds: float = 30.0
    status: str = "connected"


class PhoenixMCPClient:
    """
    Client for managing connections to external MCP servers and importing their tools safely into PHOENIX.
    """
    _instance: Optional["PhoenixMCPClient"] = None

    def __init__(self):
        self._servers: Dict[str, ExternalMCPServerConfig] = {}
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._initialize_default_external_configs()

    @classmethod
    def get_instance(cls) -> "PhoenixMCPClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_external_configs(self):
        """Pre-configure trusted external integrations with least-privilege categories."""
        defaults = [
            ExternalMCPServerConfig(
                id="github-mcp",
                name="GitHub MCP Server",
                allowed_categories=[ToolCategory.READ, ToolCategory.WRITE],
                status="ready"
            ),
            ExternalMCPServerConfig(
                id="filesystem-mcp",
                name="Controlled Filesystem MCP",
                allowed_categories=[ToolCategory.READ],
                status="ready"
            ),
            ExternalMCPServerConfig(
                id="database-mcp",
                name="Database Inspector MCP",
                allowed_categories=[ToolCategory.READ],
                status="ready"
            ),
            ExternalMCPServerConfig(
                id="docs-mcp",
                name="Documentation MCP",
                allowed_categories=[ToolCategory.READ],
                status="ready"
            )
        ]
        for cfg in defaults:
            self._servers[cfg.id] = cfg

    def list_servers(self) -> List[Dict[str, Any]]:
        return [cfg.model_dump() for cfg in self._servers.values()]

    async def register_external_server(
        self,
        server_id: str,
        name: str,
        endpoint_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        allowed_categories: Optional[List[ToolCategory]] = None
    ) -> Dict[str, Any]:
        """
        Connect to an external MCP server, discover its tools via tools/list,
        and dynamically register permitted tools into the PHOENIX ToolRegistry.
        """
        categories = allowed_categories or [ToolCategory.READ]
        cfg = ExternalMCPServerConfig(
            id=server_id,
            name=name,
            url=endpoint_url,
            auth_token=auth_token,
            allowed_categories=categories,
            status="connected"
        )
        self._servers[server_id] = cfg

        discovered_tools = []
        if endpoint_url:
            try:
                headers = {"Content-Type": "application/json"}
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}"

                # MCP 2026-07-28 tools/list handshake
                payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
                resp = await self._http_client.post(endpoint_url, json=payload, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    tools_data = data.get("result", {}).get("tools", [])
                    for t in tools_data:
                        tool_name = f"{server_id}.{t.get('name')}"
                        # Enforce category policy
                        category = ToolCategory.READ
                        if "write" in tool_name.lower() or "create" in tool_name.lower() or "update" in tool_name.lower():
                            category = ToolCategory.WRITE if ToolCategory.WRITE in categories else ToolCategory.READ

                        handler = self._create_proxy_handler(endpoint_url, t.get("name"), auth_token)
                        tool_registry.register(
                            name=tool_name,
                            description=t.get("description", f"External tool from {name}"),
                            category=category,
                            input_schema=t.get("inputSchema", {}),
                            handler=handler,
                            source=server_id
                        )
                        discovered_tools.append(tool_name)
            except Exception as e:
                logger.warning(f"Could not reach remote MCP server '{server_id}' at {endpoint_url}: {e}")
                cfg.status = "unreachable"

        return {
            "server_id": server_id,
            "status": cfg.status,
            "discovered_tools": discovered_tools
        }

    def _create_proxy_handler(self, endpoint_url: str, remote_tool_name: str, auth_token: Optional[str]):
        async def proxy_call(**arguments):
            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            payload = {
                "jsonrpc": "2.0",
                "id": "proxy-call",
                "method": "tools/call",
                "params": {"name": remote_tool_name, "arguments": arguments}
            }
            resp = await self._http_client.post(endpoint_url, json=payload, headers=headers, timeout=30.0)
            return resp.json().get("result", {})
        return proxy_call


phoenix_mcp_client = PhoenixMCPClient.get_instance()
