import socket
_orig = socket.getaddrinfo
def _patched(host, port=0, *a, **kw):
    if host in ("testserver", "localhost", "127.0.0.1"):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]
    return _orig(host, port, *a, **kw)
socket.getaddrinfo = _patched

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from httpx import AsyncClient, ASGITransport
from api import app

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpass123"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.fixture
async def client(transport):
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
