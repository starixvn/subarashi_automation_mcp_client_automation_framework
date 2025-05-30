import asyncio
import sys

from mcp_client.anthropic import MCPClient


async def run_cli():
    """Run the command-line interface."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m mcp_client.cli <URL of SSE MCP server (i.e. http://localhost:8080/sse)>"
        )
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


def main():
    """Entry point for the CLI."""
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
