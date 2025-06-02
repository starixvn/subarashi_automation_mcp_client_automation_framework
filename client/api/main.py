from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from .routes import chat, tools, health, config, prompts, resources
from .dependencies import (
    initialize_services,
    cleanup_services,
    validate_service_config,
    get_service_health,
)
from ..core.config import settings
from ..core.config_manager import is_configured, get_current_config
from ..shared.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== MCP Client API Starting ===")

    try:
        if not is_configured():
            logger.warning(
                "System not fully configured - continuing with limited functionality"
            )
            logger.info("Use /api/v1/config/update to configure the system")
        else:
            logger.info("System configuration is complete")

        config_valid = validate_service_config()
        if not config_valid:
            logger.warning("Configuration validation failed - continuing anyway")

        services_ok = True
        if is_configured():
            try:
                logger.info("Initializing services with timeout...")
                services_ok = await asyncio.wait_for(
                    initialize_services(),
                    timeout=30.0
                )
                if not services_ok:
                    logger.warning(
                        "Some services failed to initialize - continuing with degraded functionality"
                    )
            except asyncio.TimeoutError:
                logger.error("⏰ Service initialization timeout - continuing with degraded functionality")
                logger.info("💡 You can try to reconnect manually via the Configuration page")
                services_ok = False
            except Exception as e:
                logger.error(f"❌ Service initialization failed: {str(e)}")
                logger.info("💡 System will continue running with degraded functionality")
                services_ok = False

        app.state.startup_successful = services_ok
        app.state.service_health = get_service_health()
        app.state.is_configured = is_configured()

        current_config = get_current_config()
        logger.info("=== MCP Client API Started Successfully ===")
        logger.info(f"🔧 Environment: {current_config.environment}")
        logger.info(f"🔗 MCP Server: {current_config.mcp_server_url}")
        logger.info(f"🤖 AI Configured: {current_config.gemini_api_key is not None}")
        logger.info(
            f"📊 API Docs: http://{current_config.api_host}:{current_config.api_port}/docs"
        )

        yield

    except Exception as e:
        logger.error(f"=== Startup Failed: {str(e)} ===")
        app.state.startup_successful = False
        yield
    finally:
        logger.info("=== MCP Client API Shutting Down ===")
        try:
            await cleanup_services()
            logger.info("=== MCP Client API Shutdown Complete ===")
        except Exception as e:
            logger.error(f"Shutdown error: {str(e)}")


app = FastAPI(
    title="MCP Client API",
    description=(
        "Advanced MCP (Model Context Protocol) Client with Gemini AI integration.\n\n"
        "This API provides intelligent chat capabilities with automatic tool usage "
        "through MCP server connections. Features include:\n"
        "- **Configuration Management**: Set up AI and MCP server configuration\n"
        "- **Chat Interface**: Intelligent conversations with AI tool integration\n"
        "- **Tool Management**: Direct access to MCP tools and capabilities\n"
        "- **Prompt Templates**: Access and use MCP prompt templates\n"
        "- **Resource Access**: Read and subscribe to MCP resources\n"
        "- **Health Monitoring**: Comprehensive service and connection status\n"
        "- **Multi-Transport Support**: SSE, WebSocket, and stdio transports"
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://avatars.githubusercontent.com/u/14957082?s=200&v=4"
    }

    current_config = get_current_config()
    openapi_schema["servers"] = [
        {
            "url": f"http://{current_config.api_host}:{current_config.api_port}",
            "description": "Development server",
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(
    config.router,
    prefix="/api/v1/config",
    tags=["Configuration"],
    responses={
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"},
    },
)

app.include_router(
    health.router,
    prefix="/api/v1/health",
    tags=["Health & Status"],
    responses={
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)

app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["Chat & Conversation"],
    responses={
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"},
        503: {"description": "Service not configured"},
    },
)

app.include_router(
    tools.router,
    prefix="/api/v1/tools",
    tags=["Tools & MCP"],
    responses={
        404: {"description": "Tool not found"},
        500: {"description": "Internal server error"},
        503: {"description": "Service not configured"},
    },
)

app.include_router(
    prompts.router,
    prefix="/api/v1/prompts",
    tags=["Prompts & Templates"],
    responses={
        404: {"description": "Prompt not found"},
        500: {"description": "Internal server error"},
        503: {"description": "Service not configured"},
    },
)

app.include_router(
    resources.router,
    prefix="/api/v1/resources",
    tags=["Resources & Files"],
    responses={
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
        503: {"description": "Service not configured"},
    },
)


@app.get("/", tags=["Root"])
async def root():
    current_config = get_current_config()

    return {
        "name": "MCP Client API",
        "version": "2.0.0",
        "description": "Advanced MCP Client with Gemini AI integration",
        "is_configured": is_configured(),
        "environment": current_config.environment,
        "config_source": current_config.config_source,
        "endpoints": {
            "docs": "/docs",
            "config": "/api/v1/config/",
            "health": "/api/v1/health/health",
            "chat": "/api/v1/chat/chat",
            "tools": "/api/v1/tools/tools",
            "prompts": "/api/v1/prompts/prompts",
            "resources": "/api/v1/resources/resources",
        },
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    Provides consistent error responses and logging.
    """
    logger.error(f"Unhandled exception in {request.method} {request.url}: {str(exc)}")
    logger.exception("Exception details:")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": (
                str(exc) if settings.api_reload else "An unexpected error occurred"
            ),
            "path": str(request.url.path),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP exception handler for API errors.
    Provides consistent error responses for HTTP exceptions.
    """
    logger.warning(
        f"HTTP {exc.status_code} in {request.method} {request.url}: {exc.detail}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path),
        },
    )


@app.on_event("startup")
async def startup_event():
    """Additional startup tasks if needed."""
    logger.info("FastAPI startup event completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Additional shutdown tasks if needed."""
    logger.info("FastAPI shutdown event completed")


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting MCP Client API server directly")
    current_config = get_current_config()
    uvicorn.run(
        "main:app",
        host=current_config.api_host,
        port=current_config.api_port,
        reload=current_config.api_reload,
        log_level=current_config.log_level.lower(),
    )
