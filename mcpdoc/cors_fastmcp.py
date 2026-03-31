"""FastMCP subclass that enables CORS for the SSE HTTP transport."""

from __future__ import annotations

from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route


class CORSFastMCP(FastMCP):
    """FastMCP with CORS middleware so browser clients can complete preflight OPTIONS requests."""

    def __init__(
        self,
        name: str | None = None,
        instructions: str | None = None,
        *,
        cors_origins: list[str] | None = None,
        **settings: Any,
    ) -> None:
        super().__init__(name, instructions, **settings)
        if cors_origins is None or not cors_origins:
            self._cors_origins = ["*"]
        else:
            self._cors_origins = cors_origins

    async def run_sse_async(self) -> None:
        sse = SseServerTransport("/messages/")

        async def handle_root(_request: Request) -> PlainTextResponse:
            return PlainTextResponse(
                "mcpdoc SSE: use GET /sse for the MCP stream; POST to /messages/.\n",
            )

        async def handle_sse(request: Request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self._mcp_server.run(
                    streams[0],
                    streams[1],
                    self._mcp_server.create_initialization_options(),
                )

        starlette_app = Starlette(
            debug=self.settings.debug,
            routes=[
                Route("/", endpoint=handle_root),
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )
        starlette_app.add_middleware(
            CORSMiddleware,
            allow_origins=self._cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        config = uvicorn.Config(
            starlette_app,
            host=self.settings.host,
            port=self.settings.port,
            log_level=self.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()
