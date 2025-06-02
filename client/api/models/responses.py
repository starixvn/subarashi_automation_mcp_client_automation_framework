from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    """Model for tool information."""

    name: str
    description: str
    parameters: Dict[str, Any]


class ToolCallResult(BaseModel):
    """Model for tool call result."""

    success: bool
    tool_name: str
    args: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    is_error: bool = False


class PromptInfo(BaseModel):
    """Model for prompt information."""
    
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class ResourceInfo(BaseModel):
    """Model for resource information."""
    
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="AI response text")
    tool_calls: List[ToolCallResult] = Field(
        default_factory=list, description="Tool calls made during processing"
    )
    iterations: int = Field(default=0, description="Number of AI iterations")
    error: Optional[str] = Field(None, description="Error message if failed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "response": "I searched the web and found...",
                "tool_calls": [
                    {
                        "success": True,
                        "tool_name": "search_web",
                        "args": {"query": "python"},
                        "result": "Search results...",
                        "error": None,
                        "is_error": False,
                    }
                ],
                "iterations": 2,
                "error": None,
            }
        }
    }


class ToolListResponse(BaseModel):
    """Response model for tools list endpoint."""

    success: bool = Field(..., description="Whether the request was successful")
    tools: List[ToolInfo] = Field(..., description="List of available tools")
    count: int = Field(..., description="Number of tools")
    error: Optional[str] = Field(None, description="Error message if failed")


class ToolCallResponse(BaseModel):
    """Response model for tool call endpoint."""

    success: bool = Field(..., description="Whether the tool call was successful")
    tool_name: str = Field(..., description="Name of the called tool")
    result: Optional[str] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    is_error: bool = Field(False, description="Whether the result is an error")


class PromptListResponse(BaseModel):
    """Response model for prompts list endpoint."""
    
    success: bool = Field(..., description="Whether the request was successful")
    prompts: List[PromptInfo] = Field(..., description="List of available prompts")
    count: int = Field(..., description="Number of prompts")
    error: Optional[str] = Field(None, description="Error message if failed")


class PromptGetResponse(BaseModel):
    """Response model for prompt get endpoint."""
    
    success: bool = Field(..., description="Whether the request was successful")
    description: Optional[str] = Field(None, description="Prompt description")
    messages: List[Dict[str, Any]] = Field(..., description="Prompt messages")
    error: Optional[str] = Field(None, description="Error message if failed")


class ResourceListResponse(BaseModel):
    """Response model for resources list endpoint."""
    
    success: bool = Field(..., description="Whether the request was successful")
    resources: List[ResourceInfo] = Field(..., description="List of available resources")
    count: int = Field(..., description="Number of resources")
    error: Optional[str] = Field(None, description="Error message if failed")


class ResourceReadResponse(BaseModel):
    """Response model for resource read endpoint."""
    
    success: bool = Field(..., description="Whether the request was successful")
    contents: List[Dict[str, Any]] = Field(..., description="Resource contents")
    error: Optional[str] = Field(None, description="Error message if failed")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    mcp_connected: bool = Field(..., description="MCP connection status")
    server_url: Optional[str] = Field(None, description="MCP server URL")
    tools_available: int = Field(..., description="Number of available tools")
    gemini_model: str = Field(..., description="Current Gemini model")
    uptime: str = Field(..., description="Service uptime")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Server capabilities")


class ConnectionResponse(BaseModel):
    """Response model for connection status."""

    success: bool = Field(..., description="Whether the connection was successful")
    connected: bool = Field(..., description="Current connection status")
    server_url: str = Field(..., description="MCP server URL")
    tools_count: int = Field(..., description="Number of available tools")
    transport_type: Optional[str] = Field(None, description="Transport type being used")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Server capabilities")
    error: Optional[str] = Field(None, description="Error message if failed")


class StatusResponse(BaseModel):
    """Response model for service status."""

    mcp_connected: bool = Field(..., description="MCP connection status")
    server_url: str = Field(..., description="MCP server URL")
    tools_available: int = Field(..., description="Number of available tools")
    conversation_length: int = Field(..., description="Current conversation length")
    gemini_model: str = Field(..., description="Current Gemini model")
    max_iterations: int = Field(..., description="Maximum tool call iterations")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_type: Optional[str] = Field(None, description="Type of error")


class ConfigResponse(BaseModel):
    """Response model for configuration operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    config: Dict[str, Any] = Field(..., description="Configuration data")
    is_configured: bool = Field(..., description="Whether system is fully configured")
    environment: str = Field(..., description="Current environment")
    config_source: str = Field(..., description="Configuration source")
    services_reconfigured: bool = Field(False, description="Whether services were reconfigured")
    error: Optional[str] = Field(None, description="Error message if failed")


class ConfigStatusResponse(BaseModel):
    """Response model for configuration status."""

    is_configured: bool = Field(..., description="Whether system is fully configured")
    has_api_key: bool = Field(..., description="Whether API key is configured")
    environment: str = Field(..., description="Current environment")
    config_source: str = Field(..., description="Configuration source")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
