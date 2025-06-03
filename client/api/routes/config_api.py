from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ...core.core_config import (
    get_config_manager,
    get_current_config,
    update_config,
    is_configured,
    MCPClientConfig,
    settings,
)
from ..dependencies import reconfigure_services, get_tool_service, get_service_health
from ...core.session_manager import TransportType
from ...shared.logger import get_logger
from ..models.responses import ConfigResponse, ConfigStatusResponse

logger = get_logger(__name__)

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """Request model for updating configuration."""

    gemini_api_key: str = Field(..., description="Gemini API Key", min_length=1)
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp", description="Gemini model name"
    )
    mcp_server_url: str = Field(
        default="http://localhost:5000/sse", description="MCP server URL"
    )
    temperature: float = Field(
        default=0.2, ge=0.0, le=2.0, description="AI temperature"
    )
    max_tokens: int = Field(default=2000, gt=0, description="Maximum tokens")
    max_tool_calls: int = Field(default=5, gt=0, description="Maximum tool calls")
    save_to_file: bool = Field(default=True, description="Save configuration to file")


class FullConfigRequest(BaseModel):
    """Full configuration update request."""
    gemini_api_key: str = Field(..., description="Gemini API key (required)")
    gemini_model: Optional[str] = Field(None, description="Gemini model to use")
    mcp_server_url: Optional[str] = Field(None, description="MCP server URL")
    transport_type: Optional[str] = Field("sse", description="Transport type: sse, websocket, or stdio")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    max_tool_calls: Optional[int] = Field(None, gt=0)
    save_to_file: bool = Field(True, description="Save configuration to file")


@router.get("/status", response_model=ConfigStatusResponse)
async def get_config_status():
    """Get current configuration status."""
    try:
        config = get_current_config()
        manager = get_config_manager()

        missing = []
        if not config.gemini_api_key:
            missing.append("gemini_api_key")

        return ConfigStatusResponse(
            is_configured=manager.is_configured(),
            has_api_key=config.gemini_api_key is not None,
            environment=config.environment,
            config_source=config.config_source,
            missing_fields=missing,
        )

    except Exception as e:
        logger.error(f"Failed to get config status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get config status: {str(e)}"
        )


@router.get("/current", response_model=ConfigResponse)
async def get_current_configuration():
    """Get current configuration (without sensitive data)."""
    try:
        config = get_current_config()
        manager = get_config_manager()

        config_dict = {
            "gemini_model": config.gemini_model,
            "mcp_server_url": config.mcp_server_url,
            "transport_type": getattr(config, 'transport_type', 'sse'),
            "api_host": config.api_host,
            "api_port": config.api_port,
            "frontend_port": config.frontend_port,
            "log_level": config.log_level,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "max_tool_calls": config.max_tool_calls,
            "request_timeout": config.request_timeout,
            "tool_timeout": config.tool_timeout,
            "environment": config.environment,
            "has_api_key": config.gemini_api_key is not None,
        }

        return ConfigResponse(
            success=True,
            config=config_dict,
            is_configured=manager.is_configured(),
            environment=config.environment,
            config_source=config.config_source,
        )

    except Exception as e:
        logger.error(f"Failed to get current config: {str(e)}")
        return ConfigResponse(
            success=False,
            config={},
            is_configured=False,
            environment="unknown",
            config_source="unknown",
            error=str(e),
        )


@router.post("/update", response_model=ConfigResponse)
async def update_configuration(
    config_data: FullConfigRequest,
    tool_service=Depends(get_tool_service),
):
    """Update system configuration with new values."""
    try:
        if config_data.transport_type:
            try:
                TransportType(config_data.transport_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid transport type: {config_data.transport_type}. Must be one of: sse, websocket, stdio"
                )
        
        # Get current config before update for comparison
        old_config = get_current_config()
        old_url = old_config.mcp_server_url
        old_transport = getattr(old_config, 'transport_type', 'sse')
        
        updates = config_data.model_dump(exclude_none=True, exclude={"save_to_file"})
        
        success = update_config(updates, save_to_file=config_data.save_to_file)
        
        if not success:
            current_config = get_current_config()
            manager = get_config_manager()
            
            return ConfigResponse(
                success=False,
                config={},
                is_configured=manager.is_configured(),
                environment=current_config.environment,
                config_source=current_config.config_source,
                error="Failed to update configuration"
            )
        
        # Refresh settings after config update
        settings.refresh_from_config_manager()
        
        reconfigure_success = await reconfigure_services(
            config_data.gemini_api_key,
            config_data.gemini_model
        )
        
        # Get updated config after refresh
        updated_config = get_current_config()
        new_url = updated_config.mcp_server_url
        new_transport = getattr(updated_config, 'transport_type', 'sse')
        
        # Reconnect if URL or transport changed
        if new_url != old_url or new_transport != old_transport:
            try:
                logger.info(f"🔄 MCP settings changed - reconnecting...")
                logger.info(f"   Old: {old_url} via {old_transport}")
                logger.info(f"   New: {new_url} via {new_transport}")
                
                transport = TransportType(new_transport)
                await tool_service.mcp_service.disconnect()
                
                connect_success = await tool_service.mcp_service.connect(new_url, transport)
                
                if connect_success:
                    logger.info("✅ MCP reconnected successfully")
                else:
                    logger.error("❌ MCP reconnection failed")
                    
            except Exception as e:
                logger.error(f"Failed to reconnect with new settings: {str(e)}")
        
        manager = get_config_manager()
        
        config_dict = {
            "gemini_model": updated_config.gemini_model,
            "mcp_server_url": updated_config.mcp_server_url,
            "transport_type": getattr(updated_config, 'transport_type', 'sse'),
            "api_host": updated_config.api_host,
            "api_port": updated_config.api_port,
            "frontend_port": updated_config.frontend_port,
            "log_level": updated_config.log_level,
            "max_tokens": updated_config.max_tokens,
            "temperature": updated_config.temperature,
            "max_tool_calls": updated_config.max_tool_calls,
            "request_timeout": updated_config.request_timeout,
            "tool_timeout": updated_config.tool_timeout,
            "environment": updated_config.environment,
            "has_api_key": updated_config.gemini_api_key is not None,
        }
        
        return ConfigResponse(
            success=True,
            config=config_dict,
            is_configured=manager.is_configured(),
            environment=updated_config.environment,
            config_source=updated_config.config_source,
            services_reconfigured=reconfigure_success
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update configuration: {str(e)}")
        try:
            current_config = get_current_config()
            manager = get_config_manager()
        except:
            current_config = None
            manager = None
            
        return ConfigResponse(
            success=False,
            config={},
            is_configured=manager.is_configured() if manager else False,
            environment=current_config.environment if current_config else "unknown",
            config_source=current_config.config_source if current_config else "unknown",
            error=str(e)
        )


@router.post("/reset", response_model=ConfigResponse)
async def reset_configuration():
    """Reset configuration to defaults."""
    try:
        logger.info("Resetting configuration to defaults")

        updates = {
            "gemini_api_key": None,
            "gemini_model": "gemini-2.0-flash-exp",
            "mcp_server_url": "http://localhost:5000/sse",
            "transport_type": "sse",
            "temperature": 0.2,
            "max_tokens": 2000,
            "max_tool_calls": 5,
        }

        success = update_config(updates, save_to_file=False)

        current_config = get_current_config()
        manager = get_config_manager()
        
        if success:
            settings.refresh_from_config_manager()
            logger.info("Configuration reset successfully")
            
            config_dict = {
                "gemini_model": current_config.gemini_model,
                "mcp_server_url": current_config.mcp_server_url,
                "transport_type": getattr(current_config, 'transport_type', 'sse'),
                "api_host": current_config.api_host,
                "api_port": current_config.api_port,
                "frontend_port": current_config.frontend_port,
                "log_level": current_config.log_level,
                "max_tokens": current_config.max_tokens,
                "temperature": current_config.temperature,
                "max_tool_calls": current_config.max_tool_calls,
                "request_timeout": current_config.request_timeout,
                "tool_timeout": current_config.tool_timeout,
                "environment": current_config.environment,
                "has_api_key": current_config.gemini_api_key is not None,
            }
            
            return ConfigResponse(
                success=True,
                config=config_dict,
                is_configured=manager.is_configured(),
                environment=current_config.environment,
                config_source=current_config.config_source
            )
        else:
            return ConfigResponse(
                success=False,
                config={},
                is_configured=manager.is_configured(),
                environment=current_config.environment,
                config_source=current_config.config_source,
                error="Failed to reset configuration"
            )

    except Exception as e:
        logger.error(f"Config reset failed: {str(e)}")
        try:
            current_config = get_current_config()
            manager = get_config_manager()
        except:
            current_config = None
            manager = None
            
        return ConfigResponse(
            success=False,
            config={},
            is_configured=manager.is_configured() if manager else False,
            environment=current_config.environment if current_config else "unknown",
            config_source=current_config.config_source if current_config else "unknown",
            error=str(e)
        )


@router.post("/reconfigure")
async def reconfigure_services_endpoint():
    """Manually reconfigure services with current configuration."""
    try:
        config = get_current_config()

        if not config.gemini_api_key:
            return {"success": False, "error": "No API key configured"}

        logger.info("Manually reconfiguring services...")
        success = await reconfigure_services(config.gemini_api_key, config.gemini_model)

        if success:
            return {"success": True, "message": "Services reconfigured successfully"}
        else:
            return {"success": False, "error": "Service reconfiguration failed"}

    except Exception as e:
        logger.error(f"Manual reconfiguration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reconfiguration failed: {str(e)}")


@router.get("/environments")
async def get_available_environments():
    """Get list of available configuration environments."""
    try:
        return {
            "environments": [
                {
                    "name": "development",
                    "description": "Development environment with debug features",
                    "recommended_for": "Local development and testing",
                },
                {
                    "name": "production",
                    "description": "Production environment with optimized settings",
                    "recommended_for": "Production deployment",
                },
            ],
            "current": get_current_config().environment,
        }

    except Exception as e:
        logger.error(f"Failed to get environments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/environment/{environment}")
async def switch_environment(environment: str):
    """Switch to a different configuration environment."""
    try:
        if environment not in ["development", "production"]:
            raise HTTPException(status_code=400, detail="Invalid environment")

        logger.info(f"Switching to environment: {environment}")

        from ...core.core_config import load_config

        config = load_config(environment)

        settings.refresh_from_config_manager()

        logger.info(f"Switched to {environment} environment")

        return {
            "success": True,
            "environment": environment,
            "message": f"Switched to {environment} environment",
        }

    except Exception as e:
        logger.error(f"Environment switch failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Environment switch failed: {str(e)}"
        )


@router.post("/reconnect-mcp")
async def force_reconnect_mcp(
    tool_service=Depends(get_tool_service),
):
    """Force reconnect to MCP server with current configuration."""
    try:
        config = get_current_config()
        logger.info(f"🔄 Force reconnecting to MCP server: {config.mcp_server_url}")
        
        await tool_service.mcp_service.disconnect()
        
        # Get transport type
        transport_str = getattr(config, 'transport_type', 'sse')
        transport = TransportType(transport_str)
        
        # Reconnect
        connect_success = await tool_service.mcp_service.connect(
            config.mcp_server_url, 
            transport
        )
        
        if connect_success:
            # Get connection info
            connection_info = await tool_service.mcp_service.get_connection_status()
            logger.info("✅ MCP force reconnection successful")
            
            return {
                "success": True, 
                "message": "MCP server reconnected successfully",
                "connected": True,
                "server_url": config.mcp_server_url,
                "transport_type": transport_str,
                "tools_count": connection_info.get("tools_count", 0),
                "capabilities": connection_info.get("capabilities", {})
            }
        else:
            logger.error("❌ MCP force reconnection failed")
            return {
                "success": False, 
                "error": "Failed to reconnect to MCP server",
                "connected": False,
                "server_url": config.mcp_server_url
            }

    except Exception as e:
        logger.error(f"Force MCP reconnection failed: {str(e)}")
        return {
            "success": False, 
            "error": str(e),
            "connected": False
        }
