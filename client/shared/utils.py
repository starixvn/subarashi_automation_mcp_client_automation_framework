import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.types import CallToolResult


def extract_text_from_content(content: Any) -> str:
    """Extract text from various content types (MCP, Gemini, etc.)."""
    if isinstance(content, str):
        return content

    if hasattr(content, "text"):
        return content.text

    if hasattr(content, "parts"):
        text_parts = []
        for part in content.parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)
        return "\n".join(text_parts)

    return str(content)


def extract_text_from_tool_result(result: CallToolResult) -> str:
    """Extract text from MCP CallToolResult."""
    if result.isError:
        error_parts = []
        for content in result.content:
            if hasattr(content, "text"):
                error_parts.append(content.text)
        return f"Error: {' '.join(error_parts)}"

    text_parts = []
    for content in result.content:
        if hasattr(content, "text") and content.text:
            text_parts.append(content.text)

    return "\n".join(text_parts) if text_parts else "No text result"


def sanitize_tool_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize tool arguments for safe execution."""
    if not isinstance(args, dict):
        return {}

    sanitized = {}
    for key, value in args.items():
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, (list, dict)):
            sanitized[key] = json.loads(json.dumps(value))  # Deep copy
        else:
            sanitized[key] = str(value)

    return sanitized


def format_timestamp() -> str:
    """Get formatted timestamp for logging/file naming."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_tool_call_info(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Format tool call information for display."""
    args_str = json.dumps(tool_args, indent=2) if tool_args else "{}"
    return f"Tool: {tool_name}\nArguments: {args_str}"


def validate_server_url(url: str) -> bool:
    """Validate MCP server URL format."""
    if not url:
        return False

    url_lower = url.lower()
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        return False

    if not url_lower.endswith("/sse"):
        return False

    return True
