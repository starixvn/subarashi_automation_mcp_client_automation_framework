from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_tool_service
from ..models.requests import ChatRequest
from ..models.responses import ChatResponse, ToolCallResult
from ...services.tool_service import ToolService
from ...shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def process_chat(
    request: ChatRequest, tool_service: ToolService = Depends(get_tool_service)
):
    """
    Process chat message with AI and tool integration.
    Uses Gemini AI to intelligently interact with MCP tools.
    """
    try:
        logger.info(f"Processing chat message: {request.message[:100]}...")

        if request.reset_conversation:
            await tool_service.reset_conversation()
            logger.info("Conversation history reset")

        result = await tool_service.process_query(request.message)

        if result["success"]:
            tool_call_results = [
                ToolCallResult(
                    success=call["success"],
                    tool_name=call["tool_name"],
                    args=call["args"],
                    result=call.get("result"),
                    error=call.get("error"),
                    is_error=call["is_error"],
                )
                for call in result["tool_calls"]
            ]

            logger.info(
                f"Chat processed successfully with {len(tool_call_results)} tool calls"
            )

            return ChatResponse(
                success=True,
                response=result["response"],
                tool_calls=tool_call_results,
                iterations=result["iterations"],
                error=None,
            )
        else:
            logger.error(f"Chat processing failed: {result['error']}")
            return ChatResponse(
                success=False,
                response=result["response"],
                tool_calls=[],
                iterations=result["iterations"],
                error=result["error"],
            )

    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}")
        return ChatResponse(
            success=False,
            response=f"Sorry, I encountered an error: {str(e)}",
            tool_calls=[],
            iterations=0,
            error=str(e),
        )


@router.post("/reset")
async def reset_conversation(tool_service: ToolService = Depends(get_tool_service)):
    """
    Reset conversation history.
    Clears all conversation context while keeping system prompt.
    """
    try:
        await tool_service.reset_conversation()
        logger.info("Conversation history reset successfully")

        return {"success": True, "message": "Conversation history reset"}

    except Exception as e:
        logger.error(f"Failed to reset conversation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to reset conversation: {str(e)}"
        )


@router.get("/status")
async def get_chat_status(tool_service: ToolService = Depends(get_tool_service)):
    """
    Get current chat/conversation status.
    Returns information about conversation state and AI configuration.
    """
    try:
        status_info = await tool_service.get_service_status()

        return {
            "conversation_length": status_info["conversation_length"],
            "gemini_model": status_info["gemini_model"],
            "max_iterations": status_info["max_iterations"],
            "mcp_connected": status_info["mcp_connected"],
            "tools_available": status_info["tools_available"],
            "ai_configured": status_info.get("ai_configured", False),
        }

    except Exception as e:
        logger.error(f"Failed to get chat status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat status: {str(e)}"
        )


@router.get("/history")
async def get_conversation_history(
    tool_service: ToolService = Depends(get_tool_service),
):
    """
    Get conversation history summary.
    Returns basic information about the current conversation state.
    """
    try:
        status_info = await tool_service.get_service_status()

        return {
            "message_count": status_info["conversation_length"],
            "has_system_prompt": status_info["conversation_length"] > 0,
            "model": status_info["gemini_model"],
            "ai_configured": status_info.get("ai_configured", False),
        }

    except Exception as e:
        logger.error(f"Failed to get conversation history: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get conversation history: {str(e)}"
        )
