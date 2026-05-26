import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.base import Author, Post


@pytest_asyncio.fixture
async def seed(db_engine):
    """Insert seed data with its own session, cleanup after."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        author = Author(name="Ada Lovelace", email="ada@example.com")
        session.add(author)
        await session.flush()
        session.add_all([
            Post(title=f"Post {i}", body="x", author_id=author.id, status="published")
            for i in range(3)
        ])
        await session.commit()
        author_id = author.id
    yield author_id


@pytest.mark.asyncio
async def test_list_posts(client: AsyncClient, seed):
    resp = await client.get("/posts/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    assert all("author" in p for p in data)


@pytest.mark.asyncio
async def test_post_not_found(client: AsyncClient):
    resp = await client.get("/posts/99999")
    assert resp.status_code == 404
