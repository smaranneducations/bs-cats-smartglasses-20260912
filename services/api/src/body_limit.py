"""Bound actual request bytes, including chunked requests with no length header."""
from __future__ import annotations

from starlette.responses import JSONResponse


class RequestBodyLimit:
    def __init__(self, app, maximum=524288):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        guarded = (scope["type"] == "http" and scope.get("path", "").startswith("/v1")
                   and scope.get("method") not in {"GET", "HEAD", "OPTIONS"})
        if not guarded:
            await self.app(scope, receive, send)
            return
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.maximum:
                await JSONResponse({"detail": "Request exceeds the workspace limit."}, status_code=413)(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        buffered = {"type": "http.request", "body": b"".join(chunks), "more_body": False}

        async def replay():
            nonlocal buffered
            if buffered is not None:
                message, buffered = buffered, None
                return message
            return await receive()

        await self.app(scope, replay, send)
