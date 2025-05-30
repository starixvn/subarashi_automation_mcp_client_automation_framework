import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

from mcp_client.core.session_manager import SessionManager
from mcp_client.gemini.service import GeminiService
from mcp_client.browser.delegate import ClientBrowserManager
from google.genai.types import Content, Part

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiClient:
    """Main client for interacting with MCP servers using Gemini."""

    def __init__(self):
        """Initialize the MCP client with Gemini model."""
        self.session_manager = SessionManager()
        self.gemini_service = GeminiService()
        self.browser_manager = ClientBrowserManager()
        self.browser_initialized = False
        self.function_declarations = []
        self.conversation_history = []
        self.skip_tools = set()
        
        # Add system prompt
        self._initialize_system_prompt()

    def _initialize_system_prompt(self):
        """Initialize the conversation with a system prompt."""
        system_text = (
            "[SYSTEM INSTRUCTIONS - ALWAYS FOLLOW]\n"
            "You are a helpful AI assistant with access to various tools to assist users. "
            "When users request information or actions related to available tools, "
            "PROACTIVELY use appropriate tools to complete tasks without asking for further confirmation.\n\n"
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
            "EFFECTIVE PROGRESS REPORTING:\n"
            "1. Explain your analysis process and reasoning\n"
            "2. Report tool usage and outcomes clearly\n"
            "3. If encountering difficulties, explain your adaptive strategy\n"
            "4. Summarize completed tasks and achievements\n\n"
            "GENERAL PRINCIPLES:\n"
            "1. Be proactive and autonomous - solve problems without asking for guidance\n"
            "2. Think strategically rather than trying multiple similar approaches\n"
            "3. Maintain conversation context and build on previous interactions\n"
            "4. Analyze each webpage uniquely rather than applying fixed patterns\n"
            "5. Prioritize effectiveness over number of tool calls\n\n"
            "Intelligently analyze each webpage and choose the most appropriate tools and approaches for each unique situation."
        )

        system_part = Part(text=system_text)
        initial_system_message = Content(role="user", parts=[system_part])
        self.conversation_history.append(initial_system_message)

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport.

        Args:
            server_url: URL of the SSE server
        """
        await self.session_manager.connect(server_url)

        # Set up custom message handler for browser commands
        if self.session_manager.session:
            self.session_manager.session.on_custom_message = self.handle_browser_command

        # List available tools to verify connection
        print("Initialized SSE client...")
        print("Listing tools...")
        tools = await self.session_manager.list_tools()
        
        # Convert MCP tools to Gemini tools
        self.function_declarations = self.gemini_service.convert_mcp_tools_to_gemini_tools(tools)
        
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        print(f"Converted {len(self.function_declarations)} tools for Gemini")

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and available tools.

        Args:
            query: The user's query

        Returns:
            The final response text
        """
        user_part = Part(text=query)
        user_prompt_content = Content(role="user", parts=[user_part])
        self.conversation_history.append(user_prompt_content)

        try:
            response = self.gemini_service.generate_response(
                contents=self.conversation_history,
                tools=self.function_declarations
            )

            return await self.process_response(response)

        except Exception as e:
            return f"Error processing query: {str(e)}"

    async def process_response(self, response: Any) -> str:
        """Process Gemini response and handle tool calls properly."""
        final_text = []

        for candidate in response.candidates:
            if not candidate.content:
                continue

            assistant_content = candidate.content
            self.conversation_history.append(assistant_content)

            for part in assistant_content.parts:
                if hasattr(part, "text") and part.text:
                    final_text.append(part.text)

            tool_calls = []
            for part in assistant_content.parts:
                if hasattr(part, "function_call") and part.function_call is not None:
                    tool_calls.append(part.function_call)

            if not tool_calls:
                continue

            function_responses = []
            tool_results = []

            for function_call in tool_calls:
                tool_name = function_call.name
                tool_args = function_call.args

                call_info = f"[Calling tool: {tool_name} with arguments: {json.dumps(tool_args, indent=2)}]"
                print(call_info)
                tool_results.append(call_info)

                try:
                    if tool_name in self.skip_tools:
                        skip_msg = f"[Skipped problematic tool: {tool_name}]"
                        tool_results.append(skip_msg)
                        function_responses.append(
                            {
                                "name": tool_name,
                                "response": {
                                    "error": f"Tool {tool_name} is not supported"
                                },
                            }
                        )
                        continue

                    result = await self.session_manager.call_tool(
                        tool_name=tool_name, 
                        tool_args=tool_args
                    )
                    tool_result_text = self.extract_text_from_tool_result(result)
                    tool_results.append(f"[Tool result: {tool_result_text}]")

                    function_responses.append(
                        {"name": tool_name, "response": {"result": tool_result_text}}
                    )

                except Exception as e:
                    error_msg = f"Error calling tool {tool_name}: {str(e)}"
                    print(error_msg)
                    tool_results.append(error_msg)

                    function_responses.append(
                        {"name": tool_name, "response": {"error": str(e)}}
                    )

            if len(function_responses) != len(tool_calls):
                print(
                    f"WARNING: Number of function responses ({len(function_responses)}) does not match number of tool calls ({len(tool_calls)})"
                )
                while len(function_responses) < len(tool_calls):
                    function_responses.append(
                        {
                            "name": "dummy_tool",
                            "response": {
                                "error": "Placeholder response to ensure matching count"
                            },
                        }
                    )

            final_text.extend(tool_results)

            function_response_parts = []
            for response_data in function_responses:
                if "result" in response_data["response"]:
                    function_response_part = Part(
                        function_response={
                            "name": response_data["name"],
                            "response": {"result": response_data["response"]["result"]},
                        }
                    )
                else:
                    function_response_part = Part(
                        function_response={
                            "name": response_data["name"],
                            "response": {
                                "error": response_data["response"].get(
                                    "error", "Unknown error"
                                )
                            },
                        }
                    )
                function_response_parts.append(function_response_part)

            if function_response_parts:
                function_response_content = Content(
                    role="function", parts=function_response_parts
                )

                self.conversation_history.append(function_response_content)

                try:
                    follow_up_response = self.gemini_service.generate_response(
                        contents=self.conversation_history,
                        tools=self.function_declarations
                    )

                    follow_up_text = await self.process_response(follow_up_response)
                    if follow_up_text:
                        final_text.append(follow_up_text)
                except Exception as e:
                    error_msg = f"Error in follow-up response: {str(e)}"
                    print(error_msg)
                    final_text.append(error_msg)

        return "\n".join([text for text in final_text if text])

    def extract_text_from_tool_result(self, result) -> str:
        """Extract text content from MCP tool result."""
        if result.isError:
            return f"Error: {' '.join([c.text for c in result.content if hasattr(c, 'text')])}"

        text_parts = []
        for content in result.content:
            if hasattr(content, "text") and content.text:
                text_parts.append(content.text)

        return "\n".join(text_parts) if text_parts else "No text result"

    async def chat_loop(self):
        """Run an interactive chat loop."""
        print("\nGemini MCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() in ["exit", "quit"]:
                    print("Exiting chat...")
                    break

                response = await self.process_query(query)
                print(f"\nAssistant: {response}")

            except Exception as e:
                print(f"\nError in chat loop: {str(e)}")

    async def handle_browser_command(self, message):
        """Handle browser commands from server."""
        if message.get("type") != "browser_command":
            return

        command = message.get("command")
        command_id = message.get("command_id")

        logger.info(f"Received browser command: {command}")

        if not self.browser_initialized:
            await self.browser_manager.initialize()
            self.browser_initialized = True

        result = await self.browser_manager.execute_command(command)

        # Send result back to server
        await self.session_manager.session.send_custom_message(
            {"type": "browser_result", "command_id": command_id, "result": result}
        )

    async def cleanup(self):
        """Properly clean up all resources."""
        try:
            await self.session_manager.cleanup()

            # Add browser cleanup
            if self.browser_initialized:
                await self.browser_manager.close()

        except Exception as e:
            print(f"Error during cleanup: {str(e)}") 