"""
PHOENIX MCP API Router
Exposes MCP 2026-07-28 JSON-RPC endpoints and developer exploration REST APIs.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import json
import asyncio

from backend.app.core.security import get_current_user, get_optional_current_user
from backend.app.models.user import User
from backend.app.mcp.schemas import (
    JSONRPCRequest,
    JSONRPCResponse,
    ToolDefinition,
    ToolCallRequest,
    ToolCallResult,
    ResourceDefinition,
    ResourceReadResult,
    PromptDefinition,
    PromptGetResult
)
from backend.app.mcp.server import phoenix_mcp_server
from backend.app.mcp.client import phoenix_mcp_client
from backend.app.mcp.registry import tool_registry

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])


# 1. Standard MCP JSON-RPC 2.0 Core Endpoint
@router.post("", response_model=JSONRPCResponse)
async def handle_mcp_jsonrpc(
    request: JSONRPCRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Standard MCP 2026-07-28 JSON-RPC 2.0 gateway.
    Handles 'initialize', 'tools/list', 'tools/call', 'resources/list', 'resources/read', 'prompts/list', 'prompts/get'.
    """
    role = current_user.role if current_user else "developer"
    return await phoenix_mcp_server.dispatch_jsonrpc(request, user_role=role)


# 2. MCP Server-Sent Events (SSE) Endpoint
@router.get("/sse")
async def mcp_sse_stream():
    """Server-Sent Events endpoint for MCP real-time notifications and discovery."""
    async def event_generator():
        yield f"event: endpoint\ndata: /api/v1/mcp\n\n"
        while True:
            await asyncio.sleep(15)
            ping_data = json.dumps({"type": "ping", "server": "phoenix-mcp-server", "version": "2026.1.0"})
            yield f"event: ping\ndata: {ping_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# 3. REST Discovery: Tools
@router.get("/tools", response_model=List[ToolDefinition])
def list_mcp_tools():
    """List all registered MCP tools with input schemas and risk category."""
    return tool_registry.list_tools()


@router.post("/tools/call", response_model=ToolCallResult)
async def call_mcp_tool(
    req: ToolCallRequest,
    current_user: User = Depends(get_current_user)
):
    """Directly execute an MCP tool through the authorization gateway."""
    return await tool_registry.execute_tool(req, user_role=current_user.role)


# 4. REST Discovery: Resources
@router.get("/resources", response_model=List[ResourceDefinition])
def list_mcp_resources():
    """List all MCP resources exposed by PHOENIX."""
    return phoenix_mcp_server.list_resources()


@router.get("/resources/read", response_model=ResourceReadResult)
def read_mcp_resource(uri: str = Query(..., description="URI of the resource to read")):
    """Read contents of a specific MCP resource URI."""
    try:
        return phoenix_mcp_server.read_resource(uri)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 5. REST Discovery: Prompts
@router.get("/prompts", response_model=List[PromptDefinition])
def list_mcp_prompts():
    """List all available MCP prompts."""
    return phoenix_mcp_server.list_prompts()


@router.post("/prompts/get", response_model=PromptGetResult)
def get_mcp_prompt(payload: Dict[str, Any]):
    """Retrieve filled prompt template by name."""
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Field 'name' is required.")
    args = payload.get("arguments", {})
    return phoenix_mcp_server.get_prompt(name, args)


# 6. MCP Client: External Servers
@router.get("/servers")
def list_external_mcp_servers():
    """List all configured external MCP servers."""
    return phoenix_mcp_client.list_servers()


@router.post("/servers")
async def connect_external_mcp_server(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Register and connect to an external MCP server."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can connect external MCP servers.")
    
    server_id = payload.get("id")
    name = payload.get("name", server_id)
    url = payload.get("url")
    auth_token = payload.get("auth_token")

    if not server_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server 'id' is required.")

    return await phoenix_mcp_client.register_external_server(
        server_id=server_id,
        name=name,
        endpoint_url=url,
        auth_token=auth_token
    )
