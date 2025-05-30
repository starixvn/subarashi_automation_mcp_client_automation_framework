"""MCP Client Package - Supporting multiple AI services.

Examples:
    # Import Anthropic client
    from mcp_client.anthropic import MCPClient as AnthropicClient
    
    # Import Gemini client
    from mcp_client.gemini import GeminiClient
    
    # Import core components
    from mcp_client.core import SessionManager
"""

from . import anthropic
from . import core
from . import gemini
from . import browser
