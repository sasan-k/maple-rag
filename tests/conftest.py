"""
Pytest configuration and fixtures.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.main import app
from src.config.settings import Settings
from src.db.models import Base

# Test database URL (SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="development",
        debug=True,
        database_url=TEST_DATABASE_URL,
        llm_provider="openai",
        openai_api_key="test-key",
    )


@pytest.fixture
def mock_settings(test_settings: Settings):
    """Mock the settings."""
    with patch("src.config.settings.get_settings", return_value=test_settings):
        yield test_settings


@pytest_asyncio.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client."""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock LLM."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(
        return_value=MagicMock(content="This is a test response about taxes.")
    )
    return mock


@pytest.fixture
def mock_embeddings() -> MagicMock:
    """Create mock embeddings."""
    mock = MagicMock()
    mock.aembed_query = AsyncMock(return_value=[0.1] * 3072)
    mock.aembed_documents = AsyncMock(return_value=[[0.1] * 3072])
    return mock


@pytest.fixture
def sample_html() -> str:
    """Sample HTML for testing scraper."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Tax Information - Canada.ca</title>
    </head>
    <body>
        <header>
            <nav>Navigation content</nav>
        </header>
        <main>
            <h1>Tax Information</h1>
            <p>This is information about taxes in Canada.</p>
            <p>You can file your taxes online or by mail.</p>
            <section>
                <h2>Deadlines</h2>
                <p>The deadline for filing is April 30.</p>
            </section>
        </main>
        <footer>Footer content</footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_french_html() -> str:
    """Sample French HTML for testing."""
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <title>Information fiscale - Canada.ca</title>
    </head>
    <body>
        <main>
            <h1>Information fiscale</h1>
            <p>Voici des informations sur les impôts au Canada.</p>
        </main>
    </body>
    </html>
    """
