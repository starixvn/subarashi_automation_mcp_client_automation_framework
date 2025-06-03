import httpx
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import streamlit as st

current_file = Path(__file__)
project_root = current_file.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from client.core.core_config import settings


class APIClient:
    """Client for communicating with FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 120.0

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to API with error handling."""
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out"}
        except httpx.HTTPError as e:
            return {"success": False, "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    async def health_check(self) -> Dict[str, Any]:
        """Get health status of the API."""
        return await self._make_request("GET", "/api/v1/health/health")

    async def get_status(self) -> Dict[str, Any]:
        """Get detailed service status."""
        return await self._make_request("GET", "/api/v1/health/status")

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get MCP connection status."""
        return await self._make_request("GET", "/api/v1/health/connection")

    async def reconnect_server(self) -> Dict[str, Any]:
        """Reconnect to MCP server."""
        return await self._make_request("POST", "/api/v1/health/connection/reconnect")

    async def get_config_status(self) -> Dict[str, Any]:
        """Get configuration status."""
        return await self._make_request("GET", "/api/v1/config/status")

    async def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return await self._make_request("GET", "/api/v1/config/current")

    async def update_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update system configuration."""
        return await self._make_request(
            "POST", "/api/v1/config/update", json=config_data
        )

    async def reset_config(self) -> Dict[str, Any]:
        """Reset configuration to defaults."""
        return await self._make_request("POST", "/api/v1/config/reset")

    async def reconfigure_services(self) -> Dict[str, Any]:
        """Manually reconfigure services with current configuration."""
        return await self._make_request("POST", "/api/v1/config/reconfigure")

    async def get_environments(self) -> Dict[str, Any]:
        """Get available configuration environments."""
        return await self._make_request("GET", "/api/v1/config/environments")

    async def switch_environment(self, environment: str) -> Dict[str, Any]:
        """Switch to different environment."""
        return await self._make_request(
            "POST", f"/api/v1/config/environment/{environment}"
        )

    async def reconnect_mcp(self) -> Dict[str, Any]:
        """Force reconnect to MCP server with current configuration."""
        return await self._make_request("POST", "/api/v1/config/reconnect-mcp")

    async def send_chat_message(
        self, message: str, reset_conversation: bool = False
    ) -> Dict[str, Any]:
        """Send chat message to AI."""
        payload = {"message": message, "reset_conversation": reset_conversation}
        return await self._make_request("POST", "/api/v1/chat/chat", json=payload)

    async def reset_conversation(self) -> Dict[str, Any]:
        """Reset conversation history."""
        return await self._make_request("POST", "/api/v1/chat/reset")

    async def get_chat_status(self) -> Dict[str, Any]:
        """Get chat status."""
        return await self._make_request("GET", "/api/v1/chat/status")

    async def get_conversation_history(self) -> Dict[str, Any]:
        """Get conversation history summary."""
        return await self._make_request("GET", "/api/v1/chat/history")

    async def list_tools(self) -> Dict[str, Any]:
        """Get list of available tools."""
        return await self._make_request("GET", "/api/v1/tools/tools")

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a specific tool directly."""
        payload = {"tool_name": tool_name, "tool_args": tool_args}
        return await self._make_request("POST", "/api/v1/tools/call", json=payload)

    async def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool."""
        return await self._make_request("GET", f"/api/v1/tools/{tool_name}")

    async def refresh_tools(self) -> Dict[str, Any]:
        """Refresh tool list from MCP server."""
        return await self._make_request("POST", "/api/v1/tools/refresh")

    # Prompts API
    async def list_prompts(self) -> Dict[str, Any]:
        """Get list of available prompts."""
        return await self._make_request("GET", "/api/v1/prompts/prompts")

    async def get_prompt(
        self, prompt_name: str, arguments: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Get a specific prompt."""
        params = {"arguments": arguments} if arguments else {}
        return await self._make_request(
            "GET", f"/api/v1/prompts/prompts/{prompt_name}", params=params
        )

    async def list_resources(self) -> Dict[str, Any]:
        """Get list of available resources."""
        return await self._make_request("GET", "/api/v1/resources/resources")

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        return await self._make_request(
            "GET", "/api/v1/resources/resources/read", params={"uri": uri}
        )

    async def subscribe_resource(self, uri: str) -> Dict[str, Any]:
        """Subscribe to resource updates."""
        return await self._make_request(
            "POST", "/api/v1/resources/resources/subscribe", json={"uri": uri}
        )

    async def unsubscribe_resource(self, uri: str) -> Dict[str, Any]:
        """Unsubscribe from resource updates."""
        return await self._make_request(
            "POST", "/api/v1/resources/resources/unsubscribe", json={"uri": uri}
        )


_api_client = None


def get_api_client() -> APIClient:
    """Get singleton API client instance."""
    global _api_client
    if _api_client is None:
        # Import settings here to avoid circular imports
        base_url = f"http://localhost:{settings.api_port}"
        _api_client = APIClient(base_url)
    return _api_client


def run_async(coro):
    """Run async coroutine in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
