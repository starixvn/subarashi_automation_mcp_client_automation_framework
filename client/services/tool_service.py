from typing import List, Dict, Any, Optional

from google.genai.types import Content, Part

from .mcp_service import MCPService
from .gemini_service import GeminiService
from ..core.config import settings
from ..core.session_manager import TransportType
from ..core.exceptions import (
    GeminiServiceError,
    MCPToolCallError,
    ServiceNotAvailableError,
)
from ..shared.logger import get_logger

logger = get_logger(__name__)


class ToolService:
    """Advanced service for tool management and AI-driven execution with lazy initialization."""

    def __init__(self):
        self.mcp_service = MCPService()
        self.gemini_service = None
        self.conversation_history: List[Content] = []
        self.max_iterations = settings.max_tool_calls
        self._system_prompt_initialized = False

        self._try_initialize_gemini()

    def _try_initialize_gemini(self):
        """Try to initialize Gemini service if API key is available."""
        try:
            self.gemini_service = GeminiService()
            if self.gemini_service.is_configured():
                self._initialize_system_prompt()
                logger.info("Gemini service initialized in ToolService")
            else:
                logger.info(
                    "Gemini service created but not configured (waiting for API key)"
                )
        except Exception as e:
            logger.warning(f"Gemini service initialization deferred: {str(e)}")
            self.gemini_service = None

    def configure_gemini(self, api_key: str, model_name: Optional[str] = None) -> bool:
        """Configure Gemini service with API key and model."""
        try:
            if not self.gemini_service:
                self.gemini_service = GeminiService()

            success = self.gemini_service.configure(api_key, model_name)

            if success:
                self.max_iterations = settings.max_tool_calls

                if not self._system_prompt_initialized:
                    self._initialize_system_prompt()

                logger.info("ToolService configured with Gemini successfully")
                return True
            else:
                logger.error("Failed to configure Gemini in ToolService")
                return False

        except Exception as e:
            logger.error(f"Failed to configure ToolService: {str(e)}")
            return False

    def is_ai_configured(self) -> bool:
        """Check if AI (Gemini) service is configured."""
        return self.gemini_service is not None and self.gemini_service.is_configured()

    def _ensure_ai_configured(self):
        """Ensure AI service is configured before use."""
        if not self.is_ai_configured():
            if settings.gemini_api_key:
                self._try_initialize_gemini()

            if not self.is_ai_configured():
                raise ServiceNotAvailableError(
                    "AI service not configured. Please set Gemini API key via configuration."
                )

    def _initialize_system_prompt(self):
        """Initialize conversation with comprehensive system prompt."""
        if self._system_prompt_initialized:
            return

        system_text = (
            "[SYSTEM INSTRUCTIONS - ALWAYS FOLLOW]\n"
            "You are an advanced AI assistant with access to various tools through MCP (Model Context Protocol). "
            "When users request information or actions, PROACTIVELY use appropriate tools to complete tasks without asking for further confirmation.\n\n"
            "INTELLIGENT TOOL ANALYSIS:\n"
            "1. Analyze the user's request to understand the goal and required actions\n"
            "2. Examine available tools and their capabilities carefully\n"
            "3. Choose the most appropriate tools for the task at hand\n"
            "4. Use tools in logical sequence when multiple tools are needed\n"
            "5. Provide meaningful arguments based on context and requirements\n\n"
            "STRATEGIC EXECUTION:\n"
            "1. Plan your approach before executing tools - consider the most efficient sequence\n"
            "2. Execute tools with proper error handling and adaptation\n"
            "3. Analyze tool results and adjust strategy if needed\n"
            "4. Combine results from multiple tools when beneficial\n"
            "5. Provide comprehensive responses based on tool outputs\n\n"
            "INTELLIGENT WEB ANALYSIS:\n"
            "1. First, understand the user's goal (searching, clicking, reading content, etc.)\n"
            "2. Use Get-Page-HTML to get the full HTML structure of the current page\n"
            "3. Analyze the HTML structure to identify interactive elements (search boxes, buttons, forms)\n"
            "4. Look for semantic patterns in element attributes, not just fixed selectors\n"
            "5. Determine the most appropriate element for the task based on context\n\n"
            "STRATEGIC TOOL USAGE:\n"
            "1. Plan your approach before using tools - consider the most efficient sequence\n"
            "2. Use Browser-Find-By-XPath only after analyzing the page structure\n"
            "3. Try intuitive selectors based on the page's specific structure\n"
            "4. If an interaction fails, analyze the result and adjust your approach\n"
            "5. Use a single well-chosen tool action rather than multiple similar attempts\n\n"
            "ADAPTIVE ERROR HANDLING:\n"
            "1. If element selection fails, analyze why before trying alternatives\n"
            "2. Consider the website's design patterns and adjust your strategy\n"
            "3. Look for alternative paths to achieve the same goal\n"
            "4. Innovate solutions based on the specific website structure\n\n"
            "ERROR HANDLING:\n"
            "1. If a tool fails, analyze the error and try alternative approaches\n"
            "2. Explain tool failures clearly to users\n"
            "3. Continue with available information when some tools fail\n"
            "4. Suggest alternative solutions when primary tools are unavailable\n\n"
            "EFFECTIVE PROGRESS REPORTING:\n"
            "1. Explain your analysis process and reasoning\n"
            "2. Report tool usage and outcomes clearly\n"
            "3. If encountering difficulties, explain your adaptive strategy\n"
            "4. Summarize completed tasks and achievements\n\n"
            "COMMUNICATION:\n"
            "1. Explain what tools you're using and why\n"
            "2. Summarize tool results clearly and concisely\n"
            "3. Build comprehensive responses based on all tool outputs\n"
            "4. Acknowledge limitations and provide context\n\n"
            "GENERAL PRINCIPLES:\n"
            "1. Be proactive and autonomous - solve problems without asking for guidance\n"
            "2. Think strategically rather than trying multiple similar approaches\n"
            "3. Maintain conversation context and build on previous interactions\n"
            "4. Analyze each webpage uniquely rather than applying fixed patterns\n"
            "5. Prioritize effectiveness over number of tool calls\n"
            "6. Use tools proactively and intelligently to provide the best possible assistance\n\n"
            "Remember: PROACTIVELY use appropriate tools to complete tasks without asking for further confirmation. "
            "Intelligently analyze each situation and choose the most appropriate tools and approaches for each unique context."
        )

        system_part = Part(text=system_text)
        system_content = Content(role="user", parts=[system_part])
        self.conversation_history = [system_content]
        self._system_prompt_initialized = True

        logger.info("Initialized tool service with enhanced proactive system prompt")

    async def connect_to_server(self, server_url: Optional[str] = None) -> bool:
        """Connect to MCP server and prepare tools."""
        transport_str = getattr(settings, 'transport_type', 'sse')
        try:
            transport = TransportType(transport_str)
        except ValueError:
            logger.warning(f"Invalid transport type '{transport_str}', using SSE")
            transport = TransportType.SSE
            
        return await self.mcp_service.connect(server_url, transport)

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process user query with intelligent tool usage."""
        try:
            self._ensure_ai_configured()

            user_part = Part(text=query)
            user_content = Content(role="user", parts=[user_part])
            self.conversation_history.append(user_content)

            mcp_tools = await self.mcp_service.get_tools()
            gemini_tools = self.gemini_service.convert_mcp_tools_to_gemini(mcp_tools)

            response_data = await self._process_with_tools(gemini_tools)

            return {
                "success": True,
                "response": response_data["response"],
                "tool_calls": response_data["tool_calls"],
                "iterations": response_data["iterations"],
            }

        except ServiceNotAvailableError as e:
            logger.warning(f"Service not available: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "AI service is not configured. Please configure your Gemini API key in the Configuration tab.",
                "tool_calls": [],
                "iterations": 0,
            }
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": f"Sorry, I encountered an error: {str(e)}",
                "tool_calls": [],
                "iterations": 0,
            }

    async def _process_with_tools(self, gemini_tools: List) -> Dict[str, Any]:
        """Process query with iterative tool calling and recursive follow-up."""
        all_tool_calls = []
        final_responses = []
        iteration = 0

        try:
            response = await self.gemini_service.generate_response(
                contents=self.conversation_history, tools=gemini_tools
            )

            final_text = await self._process_response_recursively(
                response, gemini_tools, all_tool_calls
            )

            if final_text:
                final_responses.append(final_text)

            iteration = 1

        except Exception as e:
            logger.error(f"Error in initial processing: {str(e)}")
            final_responses.append(f"Error processing query: {str(e)}")

        final_response = (
            "\n".join(final_responses) if final_responses else "No response generated"
        )

        return {
            "response": final_response,
            "tool_calls": all_tool_calls,
            "iterations": iteration,
        }

    async def _process_response_recursively(
        self, response: Any, gemini_tools: List, all_tool_calls: List
    ) -> str:
        """Process Gemini response and handle tool calls with recursive follow-up (like mcp_client)."""
        final_text = []

        if not response.candidates:
            return ""

        candidate = response.candidates[0]
        if not candidate.content:
            return ""

        assistant_content = candidate.content
        self.conversation_history.append(assistant_content)

        text_parts = []
        tool_calls = []

        for part in assistant_content.parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)
            elif hasattr(part, "function_call") and part.function_call:
                tool_calls.append(part.function_call)

        if text_parts:
            final_text.extend(text_parts)

        if not tool_calls:
            return "\n".join(final_text)

        logger.info(f"Executing {len(tool_calls)} tool calls")
        tool_results = await self._execute_tool_calls(tool_calls)
        all_tool_calls.extend(tool_results)

        function_response_parts = []
        for tool_result in tool_results:
            if tool_result["success"]:
                response_part = Part(
                    function_response={
                        "name": tool_result["tool_name"],
                        "response": {"result": tool_result["result"]},
                    }
                )
            else:
                response_part = Part(
                    function_response={
                        "name": tool_result["tool_name"],
                        "response": {"error": tool_result["error"]},
                    }
                )
            function_response_parts.append(response_part)

        if function_response_parts:
            function_content = Content(role="function", parts=function_response_parts)
            self.conversation_history.append(function_content)

            try:
                logger.info("Generating follow-up response after tool execution")
                follow_up_response = await self.gemini_service.generate_response(
                    contents=self.conversation_history, tools=gemini_tools
                )

                follow_up_text = await self._process_response_recursively(
                    follow_up_response, gemini_tools, all_tool_calls
                )

                if follow_up_text:
                    final_text.append(follow_up_text)

            except Exception as e:
                error_msg = f"Error in follow-up response: {str(e)}"
                logger.error(error_msg)
                final_text.append(error_msg)

        return "\n".join([text for text in final_text if text])

    async def _execute_tool_calls(self, tool_calls: List) -> List[Dict[str, Any]]:
        """Execute multiple tool calls with proper error handling."""
        results = []

        for function_call in tool_calls:
            try:
                tool_name = function_call.name
                tool_args = dict(function_call.args) if function_call.args else {}

                logger.info(f"Executing tool: {tool_name}")

                result = await self.mcp_service.call_tool(tool_name, tool_args)
                results.append(result)

            except Exception as e:
                logger.error(f"Tool execution failed: {str(e)}")
                results.append(
                    {
                        "success": False,
                        "tool_name": getattr(function_call, "name", "unknown"),
                        "args": {},
                        "error": str(e),
                        "is_error": True,
                    }
                )

        return results

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get formatted list of available tools."""
        try:
            tools = await self.mcp_service.get_tools(use_cache=False)
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "No description",
                    "parameters": (
                        tool.inputSchema if hasattr(tool, "inputSchema") else {}
                    ),
                }
                for tool in tools
            ]
        except Exception as e:
            logger.error(f"Failed to get tools: {str(e)}")
            return []

    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        try:
            mcp_status = await self.mcp_service.get_connection_status()
        except Exception as e:
            logger.error(f"Failed to get MCP status: {str(e)}")
            mcp_status = {
                "connected": False,
                "server_url": settings.mcp_server_url,
                "tools_count": 0,
            }

        return {
            "mcp_connected": mcp_status["connected"],
            "server_url": mcp_status["server_url"],
            "tools_available": mcp_status["tools_count"],
            "conversation_length": len(self.conversation_history),
            "gemini_model": settings.gemini_model,
            "max_iterations": self.max_iterations,
            "ai_configured": self.is_ai_configured(),
        }

    async def reset_conversation(self):
        """Reset conversation history while keeping system prompt."""
        if self._system_prompt_initialized and self.conversation_history:
            self.conversation_history = self.conversation_history[:1]
        else:
            self.conversation_history = []
        logger.info("Conversation history reset")

    async def reinitialize_services(
        self, api_key: str, model_name: Optional[str] = None
    ) -> bool:
        """Reinitialize services with new configuration."""
        try:
            success = self.configure_gemini(api_key, model_name)

            if success:
                logger.info("Services reinitialized successfully")
                return True
            else:
                logger.error("Failed to reinitialize services")
                return False

        except Exception as e:
            logger.error(f"Failed to reinitialize services: {str(e)}")
            return False

    async def cleanup(self):
        """Clean up tool service."""
        await self.mcp_service.cleanup()
        logger.info("Tool service cleaned up")
