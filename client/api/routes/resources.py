from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.responses import ResourceListResponse, ResourceReadResponse, ErrorResponse
from ..dependencies import get_configured_tool_service, require_configuration
from ...core.exceptions import ServiceNotAvailableError
from ...shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/resources",
    response_model=ResourceListResponse,
    summary="List available resources",
    description="Get a list of all available resources from the MCP server.",
    responses={
        503: {"model": ErrorResponse, "description": "Service not configured"},
    },
)
async def list_resources(
    _: None = Depends(require_configuration),
    tool_service=Depends(get_configured_tool_service),
):
    """List all available resources from the MCP server."""
    try:
        resources_result = await tool_service.mcp_service.session_manager.list_resources()
        
        resources_info = [
            {
                "uri": str(resource.uri),
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mimeType,
            }
            for resource in resources_result.resources
        ]
        
        return ResourceListResponse(
            success=True,
            resources=resources_info,
            count=len(resources_info),
        )
        
    except ServiceNotAvailableError as e:
        logger.warning(f"Service not available: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list resources: {str(e)}")
        return ResourceListResponse(
            success=False,
            resources=[],
            count=0,
            error=str(e),
        )


@router.get(
    "/resources/read",
    response_model=ResourceReadResponse,
    summary="Read a resource",
    description="Read the contents of a resource by URI.",
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found"},
        503: {"model": ErrorResponse, "description": "Service not configured"},
    },
)
async def read_resource(
    uri: str = Query(..., description="The URI of the resource to read"),
    _: None = Depends(require_configuration),
    tool_service=Depends(get_configured_tool_service),
):
    """Read a specific resource from the MCP server."""
    try:
        result = await tool_service.mcp_service.session_manager.read_resource(uri)
        
        contents = []
        for content in result.contents:
            content_data = {
                "uri": str(content.uri),
                "mimeType": content.mimeType,
            }
            
            # Check content type
            if hasattr(content, "text"):
                content_data["text"] = content.text
            elif hasattr(content, "blob"):
                content_data["blob"] = content.blob
                
            contents.append(content_data)
        
        return ResourceReadResponse(
            success=True,
            contents=contents,
        )
        
    except ServiceNotAvailableError as e:
        logger.warning(f"Service not available: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to read resource '{uri}': {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Resource '{uri}' not found")
        return ResourceReadResponse(
            success=False,
            contents=[],
            error=str(e),
        )


@router.post(
    "/resources/subscribe",
    summary="Subscribe to resource updates",
    description="Subscribe to updates for a specific resource.",
    responses={
        503: {"model": ErrorResponse, "description": "Service not configured"},
    },
)
async def subscribe_resource(
    uri: str,
    _: None = Depends(require_configuration),
    tool_service=Depends(get_configured_tool_service),
):
    """Subscribe to resource updates from the MCP server."""
    try:
        await tool_service.mcp_service.session_manager.session.subscribe_resource(uri)
        return {"success": True, "subscribed": uri}
        
    except ServiceNotAvailableError as e:
        logger.warning(f"Service not available: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to subscribe to resource '{uri}': {str(e)}")
        return {"success": False, "error": str(e)}


@router.post(
    "/resources/unsubscribe",
    summary="Unsubscribe from resource updates",
    description="Unsubscribe from updates for a specific resource.",
    responses={
        503: {"model": ErrorResponse, "description": "Service not configured"},
    },
)
async def unsubscribe_resource(
    uri: str,
    _: None = Depends(require_configuration),
    tool_service=Depends(get_configured_tool_service),
):
    """Unsubscribe from resource updates from the MCP server."""
    try:
        await tool_service.mcp_service.session_manager.session.unsubscribe_resource(uri)
        return {"success": True, "unsubscribed": uri}
        
    except ServiceNotAvailableError as e:
        logger.warning(f"Service not available: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to unsubscribe from resource '{uri}': {str(e)}")
        return {"success": False, "error": str(e)} 