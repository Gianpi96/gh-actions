"""
Example models demonstrating proper index strategy.

Debug N+1 queries:
  1. Set DB_ECHO=true in .env → every SQL statement appears in the log
  2. Count the queries for a single request (N+1 = 1 + N per-item queries)
  3. Add selectinload/joinedload (see app/api/posts.py)
  4. Confirm with PostgreSQL:
       EXPLAIN (ANALYZE, BUFFERS)
       SELECT p.*, a.* FROM posts p JOIN authors a ON a.id = p.author_id;
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Author(Base):
    __tablename__ = "authors"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    name:       Mapped[str]      = mapped_column(String(255), nullable=False)
    email:      Mapped[str]      = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author")
    # email indexed implicitly by unique=True


class Post(Base):
    __tablename__ = "posts"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    title:      Mapped[str]      = mapped_column(String(500), nullable=False)
    body:       Mapped[str]      = mapped_column(Text, nullable=False, default="")
    status:     Mapped[str]      = mapped_column(String(50), nullable=False, default="draft")
    author_id:  Mapped[int]      = mapped_column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped["Author"] = relationship("Author", back_populates="posts")

    __table_args__ = (
        # FK index: prevents seq-scan on JOIN authors ────────────────────────
        Index("ix_posts_author_id", "author_id"),
        # Filtering by status ────────────────────────────────────────────────
        Index("ix_posts_status", "status"),
        # ORDER BY created_at DESC WHERE author_id = ? ───────────────────────
        Index("ix_posts_author_created", "author_id", "created_at"),
    )
