from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..dependencies import get_tool_service
from ..models.requests import ToolCallRequest
from ..models.responses import ToolListResponse, ToolCallResponse, ToolInfo
from ...services.tool_service import ToolService
from ...shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/tools", response_model=ToolListResponse)
async def list_tools(tool_service: ToolService = Depends(get_tool_service)):
    try:
        logger.debug("Fetching available tools from MCP server")
        tools_data = await tool_service.get_available_tools()

        tools_info = [
            ToolInfo(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
            )
            for tool in tools_data
        ]

        logger.info(f"Retrieved {len(tools_info)} tools")

        return ToolListResponse(
            success=True, tools=tools_info, count=len(tools_info), error=None
        )

    except Exception as e:
        logger.error(f"Failed to list tools: {str(e)}")
        return ToolListResponse(success=False, tools=[], count=0, error=str(e))


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(
    request: ToolCallRequest, tool_service: ToolService = Depends(get_tool_service)
):
    try:
        logger.info(f"Direct tool call: {request.tool_name}")

        result = await tool_service.mcp_service.call_tool(
            request.tool_name, request.tool_args
        )

        if result["success"]:
            logger.info(f"Tool {request.tool_name} executed successfully")
            return ToolCallResponse(
                success=True,
                tool_name=request.tool_name,
                result=result["result"],
                error=None,
                is_error=result["is_error"],
            )
        else:
            logger.error(
                f"Tool {request.tool_name} execution failed: {result['error']}"
            )
            return ToolCallResponse(
                success=False,
                tool_name=request.tool_name,
                result=None,
                error=result["error"],
                is_error=True,
            )

    except Exception as e:
        logger.error(f"Tool call failed: {str(e)}")
        return ToolCallResponse(
            success=False,
            tool_name=request.tool_name,
            result=None,
            error=str(e),
            is_error=True,
        )


@router.get("/tools/{tool_name}")
async def get_tool_info(
    tool_name: str, tool_service: ToolService = Depends(get_tool_service)
):
    try:
        logger.debug(f"Getting info for tool: {tool_name}")

        tools_data = await tool_service.get_available_tools()

        tool_info = next(
            (tool for tool in tools_data if tool["name"] == tool_name), None
        )

        if not tool_info:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        return ToolInfo(
            name=tool_info["name"],
            description=tool_info["description"],
            parameters=tool_info["parameters"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool info: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get tool info: {str(e)}"
        )


@router.post("/tools/refresh")
async def refresh_tools(tool_service: ToolService = Depends(get_tool_service)):
    try:
        logger.info("Refreshing tool list from MCP server")
        tools_data = await tool_service.mcp_service.get_tools(use_cache=False)

        tools_info = [
            ToolInfo(
                name=tool.name,
                description=tool.description or "No description",
                parameters=tool.inputSchema if hasattr(tool, "inputSchema") else {},
            )
            for tool in tools_data
        ]

        logger.info(f"Refreshed {len(tools_info)} tools")

        return ToolListResponse(
            success=True, tools=tools_info, count=len(tools_info), error=None
        )

    except Exception as e:
        logger.error(f"Failed to refresh tools: {str(e)}")
        return ToolListResponse(success=False, tools=[], count=0, error=str(e))
