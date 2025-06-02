from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from ..models.responses import PromptListResponse, PromptGetResponse, ErrorResponse
from ..dependencies import get_configured_tool_service, require_configuration
from ...core.exceptions import ServiceNotAvailableError
from ...shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/prompts",
    response_model=PromptListResponse,
    summary="List available prompts",
    description="Get a list of all available prompts from the MCP server.",
    responses={
        503: {"model": ErrorResponse, "description": "Service not configured"},
    },
)
async def list_prompts(
    _: None = Depends(require_configuration),
    tool_service=Depends(get_configured_tool_service),
):
    """List all available prompts from the MCP server."""
    try:
        prompts_result = await tool_service.mcp_service.session_manager.list_prompts()
        
        prompts_info = [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": [
                    {
                        "name": arg.name,
                        "description": arg.description,
                        "required": arg.required,
                    }
                    for arg in (prompt.arguments or [])
                ],
            }
            for prompt in prompts_result.prompts
        ]
        
        return PromptListResponse(
            success=True,
            prompts=prompts_info,
            count=len(prompts_info),
        )
        
    except ServiceNotAvailableError as e:
        logger.warning(f"Service not available: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list prompts: {str(e)}")
        return PromptListResponse(
            success=False,
            prompts=[],
            count=0,
            error=str(e),
        )


@router.get(
    "/prompts/{prompt_name}",
    response_model=PromptGetResponse,
    summary="Get a specific prompt",
    description="Get a prompt by name with optional arguments.",
    responses={
        404: {"model": ErrorResponse, "description": "Prompt not found"},
        503: {"model": ErrorResponse, "description": "Service not configured"},
    },
)
async def get_prompt(
    prompt_name: str,
    arguments: Dict[str, str] = None,
    _: None = Depends(require_configuration),
    tool_service=Depends(get_configured_tool_service),
):
    """Get a specific prompt from the MCP server."""
    try:
        result = await tool_service.mcp_service.session_manager.get_prompt(
            prompt_name, arguments
        )
        
        messages = []
        for msg in result.messages:
            message_data = {
                "role": msg.role,
                "content": {}
            }
            
            # Extract content based on type
            if hasattr(msg.content, "text"):
                message_data["content"]["text"] = msg.content.text
            elif hasattr(msg.content, "type"):
                message_data["content"]["type"] = msg.content.type
                if hasattr(msg.content, "data"):
                    message_data["content"]["data"] = msg.content.data
                    
            messages.append(message_data)
        
        return PromptGetResponse(
            success=True,
            description=result.description,
            messages=messages,
        )
        
    except ServiceNotAvailableError as e:
        logger.warning(f"Service not available: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get prompt '{prompt_name}': {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Prompt '{prompt_name}' not found")
        return PromptGetResponse(
            success=False,
            messages=[],
            error=str(e),
        ) 