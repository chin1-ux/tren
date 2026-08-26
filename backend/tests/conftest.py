import socket
_orig = socket.getaddrinfo
def _patched(host, port, *a, **kw):
    return _orig(host, port, socket.AF_INET, *a, **kw)
socket.getaddrinfo = _patched

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

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
