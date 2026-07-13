import os

# Must be set before any `app.*` import — Settings is a module-level
# singleton read once at import time. Production ALLOWED_HOSTS only lists
# real domains, which would reject the ASGI test client's "test" host.
os.environ["ALLOWED_HOSTS"] = "*"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest_asyncio.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
