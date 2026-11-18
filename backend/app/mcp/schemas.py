"""
Model Context Protocol (MCP) Schemas - MCP 2026-07-28 Specification
Provides JSON-RPC 2.0 compliant data structures for Tools, Resources, Prompts, and Protocol Messages.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPVersion(str, Enum):
    V2026_07_28 = "2026-07-28"
    LATEST = "2026-07-28"


class ToolCategory(str, Enum):
    READ = "READ"                    # Safe, read-only operations
    WRITE = "WRITE"                  # Mutates files or state, requires project permissions
    EXECUTE = "EXECUTE"              # Executes arbitrary code in sandbox, requires sandbox policy
    ADMINISTRATIVE = "ADMINISTRATIVE"# System-level operations (approvals, delivery, policy changes)


# JSON-RPC 2.0 Core Message Definitions
class JSONRPCRequest(BaseModel):
    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


# MCP Capability Schemas: Tools
class ToolInputSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: Optional[List[str]] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    name: str
    description: str
    category: ToolCategory = ToolCategory.READ
    inputSchema: ToolInputSchema
    requires_approval: bool = False


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolCallContent(BaseModel):
    type: str = "text"
    text: str


class ToolCallResult(BaseModel):
    content: List[ToolCallContent]
    isError: bool = False
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# MCP Capability Schemas: Resources
class ResourceDefinition(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = "application/json"


class ResourceContent(BaseModel):
    uri: str
    mimeType: str
    text: Optional[str] = None
    blob: Optional[str] = None


class ResourceReadResult(BaseModel):
    contents: List[ResourceContent]


# MCP Capability Schemas: Prompts
class PromptArgument(BaseModel):
    name: str
    description: Optional[str] = None
    required: bool = False


class PromptDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = Field(default_factory=list)


class PromptMessage(BaseModel):
    role: str
    content: ToolCallContent


class PromptGetResult(BaseModel):
    description: Optional[str] = None
    messages: List[PromptMessage]


# MCP Server Info & Handshake
class ServerCapabilities(BaseModel):
    tools: Dict[str, Any] = Field(default_factory=lambda: {"listChanged": True})
    resources: Dict[str, Any] = Field(default_factory=lambda: {"subscribe": False, "listChanged": True})
    prompts: Dict[str, Any] = Field(default_factory=lambda: {"listChanged": True})
    logging: Dict[str, Any] = Field(default_factory=dict)


class ImplementationInfo(BaseModel):
    name: str = "phoenix-mcp-server"
    version: str = "2026.1.0"


class InitializeResult(BaseModel):
    protocolVersion: str = MCPVersion.LATEST.value
    capabilities: ServerCapabilities = Field(default_factory=ServerCapabilities)
    serverInfo: ImplementationInfo = Field(default_factory=ImplementationInfo)
    instructions: Optional[str] = (
        "PHOENIX MCP Server provides autonomous software recovery, AST project inspection, "
        "deterministic sandboxed test validation, and cryptographic code repair governance."
    )
