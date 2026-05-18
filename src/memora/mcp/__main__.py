"""MCP Server entry point.

Usage:
    python -m memora.mcp                # stdio mode (default)
    python -m memora.mcp --sse          # SSE mode (http://127.0.0.1:8765/sse)
    python -m memora.mcp --sse --port 9000
"""

import asyncio
import sys

from memora.app import create_app
from memora.mcp.server import create_mcp_server


async def run_stdio():
    app = await create_app()
    mcp = create_mcp_server(app)
    await mcp.run_async()


async def run_sse(host: str = "127.0.0.1", port: int = 8765):
    app = await create_app()
    mcp = create_mcp_server(app)
    print(f"MCP Server (SSE) listening on http://{host}:{port}/sse")
    await mcp.run_http_async(host=host, port=port)


def main():
    args = sys.argv[1:]
    if "--sse" in args:
        port = 8765
        if "--port" in args:
            idx = args.index("--port")
            port = int(args[idx + 1])
        asyncio.run(run_sse(port=port))
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
