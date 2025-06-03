from typing import List, Dict, Any, Optional
from mcp.types import Tool, CallToolResult, TextContent, ImageContent, EmbeddedResource

from ..core.session_manager import SessionManager, TransportType
from ..core.core_config import settings
from ..core.exceptions import MCPConnectionError, MCPToolCallError
from ..shared.logger import get_logger

logger = get_logger(__name__)


class MCPService:
    """MCP service for managing connections and tools."""

    def __init__(self):
        """Initialize MCP service."""
        self.session_manager = SessionManager()
        self._tools_cache: List[Tool] = []
        logger.info("Initialized MCP Service")

    async def connect(
        self,
        server_url: Optional[str] = None,
        transport_type: TransportType = TransportType.SSE,
    ) -> bool:
        """Connect to MCP server."""
        try:
            url = server_url or settings.mcp_server_url
            success = await self.session_manager.connect(url, transport_type)

            if success:
                self._tools_cache = await self.session_manager.list_tools()
                logger.info(
                    f"✅ Connected to MCP server. {len(self._tools_cache)} tools available"
                )

            return success

        except Exception as e:
            logger.error(f"❌ Failed to connect to MCP server: {str(e)}")
            raise MCPConnectionError(f"Connection failed: {str(e)}")

    async def disconnect(self):
        """Disconnect from MCP server."""
        try:
            await self.session_manager.cleanup()
            self._tools_cache = []
            logger.info("Disconnected from MCP server")

        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")

    async def reconnect(self) -> bool:
        """Reconnect to MCP server."""
        logger.info("Reconnecting to MCP server...")
        await self.disconnect()
        return await self.connect()

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self.session_manager.is_connected

    async def get_tools(self, use_cache: bool = True) -> List[Tool]:
        """Get list of available tools."""
        if not self.is_connected:
            raise MCPConnectionError("Not connected to MCP server")

        if not use_cache or not self._tools_cache:
            self._tools_cache = await self.session_manager.list_tools()

        return self._tools_cache

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a specific tool and return properly formatted result."""
        if not self.is_connected:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            logger.debug(f"Calling tool: {tool_name} with args: {arguments}")

            result: CallToolResult = await self.session_manager.call_tool(
                tool_name, arguments
            )

            logger.debug(f"Tool {tool_name} completed successfully")

            content_text = []
            for content in result.content:
                if isinstance(content, TextContent):
                    content_text.append(content.text)
                elif isinstance(content, ImageContent):
                    content_text.append(f"[Image: {content.mimeType}]")
                elif isinstance(content, EmbeddedResource):
                    if hasattr(content.resource, "text"):
                        content_text.append(f"[Resource: {content.resource.text}]")
                    else:
                        content_text.append(f"[Resource: {content.resource.uri}]")

            return {
                "success": True,
                "tool_name": tool_name,
                "args": arguments,
                "result": (
                    "\n".join(content_text) if content_text else "No content returned"
                ),
                "is_error": result.isError if hasattr(result, "isError") else False,
            }

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {str(e)}")
            return {
                "success": False,
                "tool_name": tool_name,
                "args": arguments,
                "error": str(e),
                "is_error": True,
            }

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information."""
        connection_info = await self.session_manager.get_connection_info()

        return {
            "connected": connection_info["connected"],
            "server_url": connection_info["server_url"] or settings.mcp_server_url,
            "transport_type": connection_info.get("transport_type"),
            "tools_count": len(self._tools_cache),
            "capabilities": connection_info.get("capabilities", {}),
        }

    async def cleanup(self):
        """Clean up MCP service."""
        await self.session_manager.cleanup()
        self._tools_cache = []
        logger.info("MCP service cleaned up")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
