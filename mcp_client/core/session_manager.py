from typing import Optional, List, Tuple
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client


class SessionManager:

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._session_context = None
        self._streams_context = None
        
    async def connect(self, server_url: str) -> ClientSession:
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()

        return self.session
        
    async def list_tools(self):
        if not self.session:
            raise RuntimeError("Not connected to a server")
        response = await self.session.list_tools()
        return response.tools
        
    async def call_tool(self, tool_name: str, tool_args: dict):
        if not self.session:
            raise RuntimeError("Not connected to a server")
            
        return await self.session.call_tool(tool_name, tool_args)
        
    async def cleanup(self):
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None) 