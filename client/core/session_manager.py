import asyncio
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from enum import Enum

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.websocket import websocket_client
from mcp.types import (
    Tool, 
    CallToolResult, 
    InitializeResult,
    Resource,
    Prompt,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ReadResourceResult,
)

from .config import settings
from .exceptions import MCPConnectionError, MCPToolCallError
from ..shared.logger import get_logger

logger = get_logger(__name__)


class TransportType(Enum):
    """Supported transport types for MCP."""
    SSE = "sse"
    STDIO = "stdio"
    WEBSOCKET = "websocket"


class SessionManager:
    """Simple and reliable MCP session manager."""

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._session_context = None
        self._streams_context = None
        self._is_connected = False
        self._server_url: Optional[str] = None
        self._transport_type: Optional[TransportType] = None
        self._server_capabilities: Optional[Dict[str, Any]] = None
        self._tools_cache: List[Tool] = []
        
    async def connect(
        self, 
        server_url: str,
        transport_type: TransportType = TransportType.SSE
    ) -> bool:
        """Connect to MCP server with simple, reliable approach."""
        try:
            logger.info(f"Connecting to MCP server at {server_url} via {transport_type.value}")
            self._server_url = server_url
            self._transport_type = transport_type
            
            # Create transport based on type (simple approach)
            if transport_type == TransportType.SSE:
                self._streams_context = sse_client(url=server_url)
            elif transport_type == TransportType.WEBSOCKET:
                self._streams_context = websocket_client(url=server_url)
            elif transport_type == TransportType.STDIO:
                # Parse stdio parameters from URL format
                command, *args = server_url.split()
                params = StdioServerParameters(command=command, args=args)
                self._streams_context = stdio_client(server=params)
            else:
                raise MCPConnectionError(f"Unsupported transport: {transport_type}")
            
            # Simple connection without complex timeout handling
            streams = await self._streams_context.__aenter__()
            self._session_context = ClientSession(*streams)
            self.session = await self._session_context.__aenter__()
            
            # Initialize session
            init_result = await self.session.initialize()
            self._server_capabilities = init_result.capabilities.model_dump()
            
            self._is_connected = True
            logger.info(f"✅ Successfully connected to MCP server")
            logger.info(f"Server: {init_result.serverInfo.name} v{init_result.serverInfo.version}")
            logger.info(f"Capabilities: {list(self._server_capabilities.keys())}")
            
            # Cache tools if available
            if self._server_capabilities.get("tools"):
                await self._refresh_tools_cache()
            
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to MCP server: {str(e)}")
            await self._cleanup_failed_connection()
            raise MCPConnectionError(f"Connection failed: {str(e)}")

    async def list_tools(self) -> List[Tool]:
        """List available tools from MCP server."""
        if not self._is_connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            logger.debug("Requesting tools from MCP server")
            result = await self.session.list_tools()
            
            self._tools_cache = result.tools
            logger.info(f"Retrieved {len(self._tools_cache)} tools from MCP server")
            return self._tools_cache

        except Exception as e:
            logger.error(f"Failed to list tools: {str(e)}")
            raise MCPToolCallError(f"Tool listing failed: {str(e)}")

    async def call_tool(self, tool_name: str, tool_args: dict) -> CallToolResult:
        """Call a specific tool via MCP session."""
        if not self._is_connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            logger.info(f"Calling tool '{tool_name}' with args: {tool_args}")
            result = await self.session.call_tool(tool_name, tool_args)
            logger.info(f"Tool '{tool_name}' executed successfully")
            return result

        except Exception as e:
            logger.error(f"Tool '{tool_name}' call failed: {str(e)}")
            raise MCPToolCallError(f"Tool '{tool_name}' failed: {str(e)}")
    
    async def list_prompts(self) -> ListPromptsResult:
        """List available prompts from MCP server."""
        if not self._is_connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")
            
        if not self._server_capabilities.get("prompts"):
            return ListPromptsResult(prompts=[])
            
        return await self.session.list_prompts()
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, str]] = None) -> GetPromptResult:
        """Get a specific prompt from MCP server."""
        if not self._is_connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")
            
        return await self.session.get_prompt(name, arguments)
    
    async def list_resources(self) -> ListResourcesResult:
        """List available resources from MCP server."""
        if not self._is_connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")
            
        if not self._server_capabilities.get("resources"):
            return ListResourcesResult(resources=[])
            
        return await self.session.list_resources()
    
    async def read_resource(self, uri: str) -> ReadResourceResult:
        """Read a specific resource from MCP server."""
        if not self._is_connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")
            
        return await self.session.read_resource(uri)

    async def cleanup(self):
        """Clean up all connection resources - simple approach."""
        try:
            logger.info("Cleaning up MCP session")
            
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._streams_context:
                await self._streams_context.__aexit__(None, None, None)
                
            logger.info("MCP session cleaned up successfully")

        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
        finally:
            self._reset_connection_state()

    async def _cleanup_failed_connection(self):
        """Clean up resources after failed connection."""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._streams_context:
                await self._streams_context.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {str(e)}")
        finally:
            self._reset_connection_state()

    def _reset_connection_state(self):
        """Reset connection state variables."""
        self.session = None
        self._session_context = None
        self._streams_context = None
        self._is_connected = False
        self._server_url = None
        self._server_capabilities = None
        self._tools_cache = []

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._is_connected and self.session is not None

    @property
    def server_url(self) -> Optional[str]:
        """Get current server URL."""
        return self._server_url
    
    @property 
    def server_capabilities(self) -> Optional[Dict[str, Any]]:
        """Get server capabilities."""
        return self._server_capabilities
    
    @property
    def transport_type(self) -> Optional[TransportType]:
        """Get current transport type."""
        return self._transport_type

    async def _refresh_tools_cache(self):
        """Refresh cached tools from server."""
        try:
            await self.list_tools()
        except Exception as e:
            logger.error(f"Failed to refresh tools cache: {str(e)}")
            self._tools_cache = []

    async def get_connection_info(self) -> dict:
        """Get detailed connection information."""
        return {
            "connected": self.is_connected,
            "server_url": self.server_url,
            "transport_type": self.transport_type.value if self.transport_type else None,
            "session_active": self.session is not None,
            "capabilities": self._server_capabilities,
            "tools_count": len(self._tools_cache),
        }
