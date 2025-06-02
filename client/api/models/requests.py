from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User message to process")
    reset_conversation: bool = Field(
        default=False, description="Reset conversation history"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Hello, can you help me browse the web?",
                "reset_conversation": False,
            }
        }
    }


class ToolCallRequest(BaseModel):
    """Request model for direct tool calls."""

    tool_name: str = Field(..., description="Name of the tool to call")
    tool_args: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tool_name": "search_web",
                "tool_args": {"query": "python tutorial"},
            }
        }
    }


class ConnectionRequest(BaseModel):
    """Request model for MCP server connection."""

    server_url: str = Field(..., description="MCP server URL with SSE endpoint")

    model_config = {
        "json_schema_extra": {"example": {"server_url": "http://localhost:5000/sse"}}
    }


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates."""

    gemini_model: Optional[str] = Field(None, description="Gemini model to use")
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Generation temperature"
    )
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens to generate"
    )
    max_tool_calls: Optional[int] = Field(
        None, gt=0, description="Maximum tool call iterations"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "gemini_model": "gemini-2.0-flash-exp",
                "temperature": 0.2,
                "max_tokens": 2000,
                "max_tool_calls": 5,
            }
        }
    }
