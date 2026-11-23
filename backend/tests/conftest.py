# Why: Shared pytest fixtures. Sets up a test HTTP client that talks to
# the FastAPI app WITHOUT needing a running server or database.

import sys
import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


# On Windows, ProactorEventLoop (the default in Python 3.12) can hang
# with ASGI transports. SelectorEventLoop fixes this.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
async def client():
    """
    Async HTTP client that sends requests directly to the ASGI app.
    ASGITransport: bypasses the network — requests go straight to FastAPI
    in-process, making tests fast and not requiring uvicorn to be running.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
