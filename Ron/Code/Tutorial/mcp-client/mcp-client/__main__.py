import asyncio

from mcp_client.mcp_client import MCPClient

async def main():
    async with MCPClient("./mcp_server/mcp_server.py"):
        print("Connected to the MCP server!")

if __name__ == "__main__":
    asyncio.run(main())