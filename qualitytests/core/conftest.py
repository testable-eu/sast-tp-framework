import asyncio
import pytest_asyncio

# IMPORTANT: This solves the issue of some tests that were failing when run in a batch.
@pytest_asyncio.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()