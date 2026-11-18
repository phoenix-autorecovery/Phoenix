"""
PHOENIX MCP Tool Registry & Authorization Gateway
Central repository for all MCP tools with risk tier classification, schema validation, and authorization gates.
"""
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from backend.app.mcp.schemas import (
    ToolCategory,
    ToolDefinition,
    ToolCallRequest,
    ToolCallResult,
    ToolCallContent,
    ToolInputSchema
)

logger = logging.getLogger("phoenix.mcp.registry")


class RegisteredTool:
    def __init__(
        self,
        definition: ToolDefinition,
        handler: Callable[..., Any],
        source: str = "builtin"
    ):
        self.definition = definition
        self.handler = handler
        self.source = source

    async def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolCallResult:
        try:
            # Check if handler is async or sync
            sig = inspect.signature(self.handler)
            kwargs = {}
            for param_name in sig.parameters:
                if param_name in arguments:
                    kwargs[param_name] = arguments[param_name]
                elif param_name == "context":
                    kwargs["context"] = context or {}

            if inspect.iscoroutinefunction(self.handler):
                result = await self.handler(**kwargs)
            else:
                result = self.handler(**kwargs)

            # Format result as JSON string or text
            if isinstance(result, str):
                text_content = result
            elif isinstance(result, (dict, list)):
                text_content = json.dumps(result, indent=2, default=str)
            else:
                text_content = str(result)

            return ToolCallResult(
                content=[ToolCallContent(type="text", text=text_content)],
                isError=False,
                metadata={"source": self.source, "category": self.definition.category.value}
            )
        except Exception as e:
            logger.error(f"Error executing tool '{self.definition.name}': {e}", exc_info=True)
            return ToolCallResult(
                content=[ToolCallContent(type="text", text=f"Tool execution failed: {str(e)}")],
                isError=True,
                metadata={"source": self.source, "error": str(e)}
            )


class ToolRegistry:
    """
    Centralized tool registry managing tool discovery, permission classification, and execution.
    """
    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        input_schema: Dict[str, Any],
        handler: Callable[..., Any],
        source: str = "builtin",
        requires_approval: bool = False
    ) -> None:
        """Register a tool with category and JSON schema."""
        definition = ToolDefinition(
            name=name,
            description=description,
            category=category,
            inputSchema=ToolInputSchema(
                type="object",
                properties=input_schema.get("properties", {}),
                required=input_schema.get("required", [])
            ),
            requires_approval=requires_approval
        )
        self._tools[name] = RegisteredTool(definition, handler, source=source)
        logger.info(f"Registered MCP tool: '{name}' [{category.value}] (source: {source})")

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        """List all tools, optionally filtered by risk category."""
        tools = [t.definition for t in self._tools.values()]
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        return self._tools.get(name)

    async def execute_tool(
        self,
        request: ToolCallRequest,
        user_role: str = "developer",
        context: Optional[Dict[str, Any]] = None
    ) -> ToolCallResult:
        """
        Execute tool with category-based permission checks.
        - READ: developer, admin, viewer
        - WRITE: developer, admin
        - EXECUTE: developer, admin
        - ADMINISTRATIVE: admin only
        """
        tool = self._tools.get(request.name)
        if not tool:
            return ToolCallResult(
                content=[ToolCallContent(type="text", text=f"Tool '{request.name}' not found.")],
                isError=True
            )

        # Policy checks
        cat = tool.definition.category
        if cat == ToolCategory.ADMINISTRATIVE and user_role != "admin":
            return ToolCallResult(
                content=[ToolCallContent(
                    type="text",
                    text=f"Permission denied: Tool '{request.name}' requires administrative role (current: {user_role})."
                )],
                isError=True,
                metadata={"blocked_by_policy": True}
            )

        if cat in (ToolCategory.WRITE, ToolCategory.EXECUTE) and user_role not in ("admin", "developer"):
            return ToolCallResult(
                content=[ToolCallContent(
                    type="text",
                    text=f"Permission denied: Tool '{request.name}' requires developer or admin privileges."
                )],
                isError=True,
                metadata={"blocked_by_policy": True}
            )

        return await tool.execute(request.arguments, context=context)


# Global singleton instance
tool_registry = ToolRegistry.get_instance()
