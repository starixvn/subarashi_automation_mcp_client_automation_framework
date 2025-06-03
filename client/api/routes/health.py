import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ..dependencies import get_tool_service
from ..models.responses import HealthResponse, StatusResponse, ConnectionResponse
from ...services.tool_service import ToolService
from ...core.core_config import settings, is_configured, get_current_config
from ...shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

STARTUP_TIME = datetime.now()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check if the API is healthy and get basic service information.",
)
async def health_check():
    """Perform health check and return service status."""
    current_config = get_current_config()
    uptime = datetime.now() - STARTUP_TIME
    
    try:
        tool_service = get_tool_service()
        mcp_connected = tool_service.mcp_service.is_connected
        tools_count = len(tool_service._tools_cache) if hasattr(tool_service, '_tools_cache') else 0
        
        capabilities = None
        if mcp_connected:
            connection_info = await tool_service.mcp_service.get_connection_status()
            capabilities = connection_info.get("capabilities")
        
        status = "healthy" if mcp_connected else "degraded"
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        mcp_connected = False
        tools_count = 0
        capabilities = None
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        version="2.0.0",
        mcp_connected=mcp_connected,
        server_url=current_config.mcp_server_url,
        tools_available=tools_count,
        gemini_model=current_config.gemini_model,
        uptime=f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m",
        capabilities=capabilities,
    )


@router.get(
    "/connection",
    response_model=ConnectionResponse,
    summary="Get MCP connection status",
    description="Get detailed information about the MCP server connection.",
)
async def get_connection_status(
    tool_service=Depends(get_tool_service),
):
    """Get MCP connection status."""
    try:
        if not tool_service.mcp_service.is_connected:
            return ConnectionResponse(
                success=True,
                connected=False,
                server_url=settings.mcp_server_url,
                tools_count=0,
                transport_type=None,
                capabilities=None,
            )
        
        connection_info = await tool_service.mcp_service.get_connection_status()
        
        return ConnectionResponse(
            success=True,
            connected=connection_info["connected"],
            server_url=connection_info["server_url"],
            tools_count=connection_info["tools_count"],
            transport_type=connection_info.get("transport_type"),
            capabilities=connection_info.get("capabilities"),
        )
        
    except Exception as e:
        logger.error(f"Failed to get connection status: {str(e)}")
        return ConnectionResponse(
            success=False,
            connected=False,
            server_url=settings.mcp_server_url,
            tools_count=0,
            error=str(e),
        )


@router.post(
    "/connection/reconnect",
    summary="Reconnect to MCP server",
    description="Attempt to reconnect to the MCP server.",
)
async def reconnect_server(
    tool_service=Depends(get_tool_service),
):
    """Reconnect to MCP server."""
    try:
        connected = await tool_service.mcp_service.reconnect()
        
        if connected:
            connection_info = await tool_service.mcp_service.get_connection_status()
            return {
                "success": True,
                "connected": True,
                "tools_count": connection_info["tools_count"],
                "transport_type": connection_info.get("transport_type"),
                "capabilities": connection_info.get("capabilities"),
            }
        else:
            return {
                "success": False,
                "connected": False,
                "error": "Failed to reconnect",
            }
            
    except Exception as e:
        logger.error(f"Failed to reconnect: {str(e)}")
        return {
            "success": False,
            "connected": False,
            "error": str(e),
        }


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Get service status",
    description="Get detailed status information about the service.",
)
async def get_status(
    tool_service=Depends(get_tool_service),
):
    """Get comprehensive service status."""
    try:
        status_info = await tool_service.get_service_status()
        
        return StatusResponse(
            mcp_connected=status_info["mcp_connected"],
            server_url=status_info["server_url"],
            tools_available=status_info["tools_available"],
            conversation_length=status_info["conversation_length"],
            gemini_model=status_info["gemini_model"],
            max_iterations=status_info["max_iterations"],
        )
        
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        current_config = get_current_config()
        return StatusResponse(
            mcp_connected=False,
            server_url=current_config.mcp_server_url,
            tools_available=0,
            conversation_length=0,
            gemini_model=current_config.gemini_model,
            max_iterations=current_config.max_tool_calls,
        )


def _format_uptime(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m {secs}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
