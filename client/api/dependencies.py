import asyncio
from functools import lru_cache
from typing import Dict, Any
from contextlib import asynccontextmanager

from ..services.tool_service import ToolService
from ..core.core_config import settings, is_configured, get_current_config
from ..shared.logger import get_logger

logger = get_logger(__name__)

_tool_service: ToolService = None
_service_lock = asyncio.Lock()


@lru_cache()
def get_tool_service() -> ToolService:
    global _tool_service

    if _tool_service is None:
        logger.info("Creating ToolService singleton instance")
        try:
            _tool_service = ToolService()
            logger.info("ToolService created successfully")
        except Exception as e:
            logger.error(f"Failed to create ToolService: {str(e)}")
            _tool_service = ToolService()

    return _tool_service


async def initialize_services():
    """Initialize application services if configuration is complete."""
    async with _service_lock:
        logger.info("Initializing application services")

        try:
            tool_service = get_tool_service()
            current_config = get_current_config()

            logger.info(
                f"Attempting to connect to MCP server at {current_config.mcp_server_url}"
            )
            try:
                connected = await asyncio.wait_for(
                    tool_service.connect_to_server(), timeout=10.0
                )

                if connected:
                    logger.info(
                        "✅ Successfully connected to MCP server during startup"
                    )
                    try:
                        tools = await asyncio.wait_for(
                            tool_service.get_available_tools(), timeout=5.0
                        )
                        logger.info(f"🛠️ Found {len(tools)} available tools")
                    except asyncio.TimeoutError:
                        logger.warning(
                            "⚠️ Timeout getting tools, but connection is established"
                        )
                else:
                    logger.warning("⚠️ Failed to connect to MCP server during startup")

            except asyncio.TimeoutError:
                logger.warning(
                    "⏰ MCP connection timeout during startup - server may be slow or unreachable"
                )
                logger.info(
                    "💡 System will continue running. You can reconnect manually via the UI"
                )
            except Exception as e:
                logger.warning(f"⚠️ MCP connection failed during startup: {str(e)}")
                logger.info(
                    "💡 System will continue running. Check your MCP server configuration"
                )

            if is_configured() and current_config.gemini_api_key:
                try:
                    ai_configured = tool_service.configure_gemini(
                        current_config.gemini_api_key, current_config.gemini_model
                    )
                    if ai_configured:
                        logger.info("✅ AI service configured during startup")
                    else:
                        logger.warning(
                            "⚠️ Failed to configure AI service during startup"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ AI service configuration failed: {str(e)}")
            else:
                logger.info("ℹ️ AI service not configured (API key not available)")

            return True

        except Exception as e:
            logger.error(f"❌ Service initialization failed: {str(e)}")
            return False


async def reconfigure_services(api_key: str, model_name: str = None) -> bool:
    """Reconfigure services with new API key and model."""
    async with _service_lock:
        logger.info("Reconfiguring services with new configuration")

        try:
            tool_service = get_tool_service()

            success = await tool_service.reinitialize_services(api_key, model_name)

            if success:
                logger.info("Services reconfigured successfully")
                return True
            else:
                logger.error("Failed to reconfigure services")
                return False

        except Exception as e:
            logger.error(f"Service reconfiguration failed: {str(e)}")
            return False


async def cleanup_services():
    """
    Cleanup all services during application shutdown.
    Ensures proper resource cleanup and connection closure.
    """
    global _tool_service

    async with _service_lock:
        logger.info("Cleaning up application services")

        try:
            if _tool_service:
                await _tool_service.cleanup()
                logger.info("ToolService cleaned up successfully")

            _tool_service = None

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")


def get_service_health() -> Dict[str, Any]:
    """
    Get health status of all services.
    Returns service availability and basic status information.
    """
    try:
        configured = is_configured()
        current_config = get_current_config()

        health_info = {
            "services_initialized": _tool_service is not None,
            "is_configured": configured,
            "environment": current_config.environment,
            "config_source": current_config.config_source,
        }

        if _tool_service:
            tool_service = get_tool_service()
            health_info.update(
                {
                    "tool_service": "available",
                    "mcp_connected": tool_service.mcp_service.session_manager.is_connected,
                    "ai_configured": tool_service.is_ai_configured(),
                }
            )
        else:
            health_info.update(
                {
                    "tool_service": "not_initialized",
                    "mcp_connected": False,
                    "ai_configured": False,
                }
            )

        return health_info

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "tool_service": "error",
            "mcp_connected": False,
            "ai_configured": False,
            "services_initialized": False,
            "is_configured": False,
            "error": str(e),
        }


@asynccontextmanager
async def get_tool_service_context():
    """
    Context manager for tool service operations.
    Ensures proper resource management for operations that need cleanup.
    """
    tool_service = get_tool_service()
    try:
        yield tool_service
    except Exception as e:
        logger.error(f"Error in tool service context: {str(e)}")
        raise
    finally:
        pass


def validate_service_config() -> bool:
    """Validate service configuration (non-critical)."""
    try:
        current_config = get_current_config()

        if not current_config.mcp_server_url:
            logger.error("MCP_SERVER_URL is not configured")
            return False

        if not current_config.mcp_server_url.endswith("/sse"):
            logger.warning("MCP server URL should end with '/sse' for SSE transport")

        logger.info("Basic service configuration validation passed")
        return True

    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        return False


def require_configuration():
    """Dependency that ensures system is configured (non-blocking)."""
    pass


def get_configured_tool_service() -> ToolService:
    """Get tool service (configuration is optional now)."""
    return get_tool_service()


def reset_services():
    """Reset service instances (for testing or reconfiguration)."""
    global _tool_service

    if _tool_service:
        logger.info("Resetting service instances")
        _tool_service = None

    get_tool_service.cache_clear()
