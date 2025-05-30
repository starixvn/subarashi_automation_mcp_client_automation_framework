import asyncio
import sys

from mcp_client.gemini import GeminiClient


async def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python client_gemini.py <URL of SSE MCP server (i.e. http://localhost:8080/sse)>"
        )
        sys.exit(1)

    client = GeminiClient()
    try:
        await client.connect_to_sse_server(server_url=sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
