from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    theme: Mapped[str] = mapped_column(String(32), default="midnight")
    font: Mapped[str] = mapped_column(String(32), default="inter")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class ApiToken(Base):
    __tablename__ = "api_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    prefix: Mapped[str] = mapped_column(String(12))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scope: Mapped[str] = mapped_column(String(10), default="write")  # read | write
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class PromptRecord(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    tool: Mapped[str] = mapped_column(String(16), default="claude")  # claude | codex
    spec: Mapped[str] = mapped_column(Text, default="{}")  # JSON wizard answers
    prompt_md: Mapped[str] = mapped_column(Text, default="")
    context_md: Mapped[str] = mapped_column(Text, default="")  # CLAUDE.md / AGENTS.md
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Logo(Base):
    __tablename__ = "logos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_id: Mapped[int | None] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    filename: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
