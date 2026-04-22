import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://scievent:scievent@localhost:5433/scievent_test",
)


@pytest.fixture
async def test_engine():
    from app.models.base import Base
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_db(test_engine):
    yield
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE users, otp_codes, refresh_tokens, "
                "events, slots, talks, user_slot_selections "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
async def db(test_engine) -> AsyncSession:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncClient:
    from app.database import get_db
    from app.main import app

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
