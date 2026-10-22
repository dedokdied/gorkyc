import os
import re

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# IMPORTANT: configure the test database before importing app modules.
_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/assistant"
_base_url = os.getenv("DATABASE_URL", _DEFAULT_DATABASE_URL)
_base = make_url(_base_url)
if _base.database and _base.database.endswith("_test"):
    _test_url = _base.render_as_string(hide_password=False)
else:
    _test_url = _base.set(database=f"{_base.database or 'assistant'}_test").render_as_string(hide_password=False)
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", _test_url)
os.environ.setdefault("APP_ENV", "test")

from app.db import Base, get_db
from app.main import app


async def _ensure_test_database() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    database = url.database or ""
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise RuntimeError(f"unsafe test database name: {database!r}")

    admin_url = url.set(database="postgres").render_as_string(hide_password=False)
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database},
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        await admin_engine.dispose()


@pytest_asyncio.fixture
async def db_engine():
    await _ensure_test_database()
    engine = create_async_engine(os.environ["DATABASE_URL"], future=True)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
