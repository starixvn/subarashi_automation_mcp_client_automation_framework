class MCPClientError(Exception):
    """Base exception for all MCP Client errors."""

    pass


class MCPConnectionError(MCPClientError):
    """Raised when MCP server connection fails."""

    pass


class MCPToolCallError(MCPClientError):
    """Raised when MCP tool execution fails."""

    pass


class GeminiServiceError(MCPClientError):
    """Raised when Gemini AI service encounters errors."""

    pass


class ConfigurationError(MCPClientError):
    """Raised when application configuration is invalid."""

    pass


class ValidationError(MCPClientError):
    """Raised when request/response validation fails."""

    pass


class ServiceNotAvailableError(MCPClientError):
    """Raised when a required service is not available."""

    pass


class ToolConversionError(MCPClientError):
    """Raised when MCP tool conversion to Gemini format fails."""

    pass


class SessionError(MCPClientError):
    """Raised when session management encounters errors."""

    pass
