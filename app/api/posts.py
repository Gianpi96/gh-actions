"""
N+1 query patterns and their fixes.

Bad endpoint  → 1 + N queries (1 for posts list, N for each author)
Good endpoint → 2 queries   (selectinload)  or 1 query (joinedload)

To see the difference live:
  1. Set DB_ECHO=true in .env
  2. Hit /posts/bad  → count SQL statements in log
  3. Hit /posts/     → count SQL statements (should be 2)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.models.base import Author, Post

router = APIRouter(prefix="/posts", tags=["posts"])


# ── BAD: N+1 ──────────────────────────────────────────────────────────────────
@router.get("/bad", deprecated=True)
async def get_posts_n1(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post))
    posts = result.scalars().all()
    # Accessing .author would trigger a lazy load per post in sync SQLAlchemy.
    # In async SQLAlchemy this raises MissingGreenlet, exposing the bug early.
    return [{"id": p.id, "title": p.title} for p in posts]


# ── GOOD: selectinload — 2 queries, no JOIN ───────────────────────────────────
# Query 1: SELECT * FROM posts
# Query 2: SELECT * FROM authors WHERE id IN (1, 2, 3, ...)
# Best for: one-to-many, large result sets (JOIN would create duplicate rows)
@router.get("/")
async def get_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()
    return [
        {"id": p.id, "title": p.title, "author": p.author.name}
        for p in posts
    ]


# ── GOOD: joinedload — 1 query with LEFT JOIN ─────────────────────────────────
# Best for: many-to-one (every post has exactly one author)
# Requires .unique() because the JOIN can create duplicate row objects.
@router.get("/joined")
async def get_posts_joined(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post)
        .options(joinedload(Post.author))
        .order_by(Post.created_at.desc())
    )
    posts = result.unique().scalars().all()
    return [
        {"id": p.id, "title": p.title, "author": p.author.name}
        for p in posts
    ]


# ── GOOD: nested eager load ───────────────────────────────────────────────────
@router.get("/{post_id}")
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post)
        .options(joinedload(Post.author).selectinload(Author.posts))
        .where(Post.id == post_id)
    )
    post = result.unique().scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return {
        "id": post.id,
        "title": post.title,
        "author": post.author.name,
        "author_post_count": len(post.author.posts),
    }
