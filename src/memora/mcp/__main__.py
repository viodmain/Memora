"""MCP Server entry point — run with: python -m memora.mcp"""

import asyncio
from memora.app import create_app
from memora.mcp.server import create_mcp_server


async def main():
    app = await create_app()
    mcp = create_mcp_server(app)
    await mcp.run_async()


if __name__ == "__main__":
    asyncio.run(main())
