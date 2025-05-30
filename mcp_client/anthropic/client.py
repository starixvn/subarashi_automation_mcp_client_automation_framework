import asyncio
from typing import Optional, List

from mcp_client.anthropic.service import AnthropicService
from mcp_client.core.session_manager import SessionManager
from mcp_client.anthropic.query_processor import QueryProcessor


class MCPClient:
    def __init__(self):
        self.session_manager = SessionManager()
        self.anthropic_service = AnthropicService()
        self.query_processor = QueryProcessor(
            session_manager=self.session_manager,
            anthropic_service=self.anthropic_service,
        )

    async def connect_to_sse_server(self, server_url: str):
        await self.session_manager.connect(server_url)

        print("Initialized SSE client...")
        print("Listing tools...")
        tools = await self.session_manager.list_tools()
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        return await self.query_processor.process_query(query)

    async def chat_loop(self):
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.session_manager.cleanup()
