import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from krada.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class School(TimestampMixin, Base):
    __tablename__ = "schools"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))


class SchoolClass(TimestampMixin, Base):
    __tablename__ = "school_classes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), index=True)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("school_classes.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(24), default="student")
    external_identities: Mapped[list["ExternalIdentity"]] = relationship(
        cascade="all, delete-orphan"
    )


class ExternalIdentity(TimestampMixin, Base):
    __tablename__ = "external_identities"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(128))


class Character(TimestampMixin, Base):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("user_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    class_key: Mapped[str] = mapped_column(String(40))
    level: Mapped[int] = mapped_column(default=1)
    xp: Mapped[int] = mapped_column(default=0)
    visual_seed: Mapped[int] = mapped_column(Integer)


class Raid(TimestampMixin, Base):
    __tablename__ = "raid_instances"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id"), index=True)
    state: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    question_key: Mapped[str] = mapped_column(String(64))
    score: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=1)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuestionAttempt(TimestampMixin, Base):
    __tablename__ = "question_attempts"
    __table_args__ = (UniqueConstraint("raid_id", "user_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), index=True)
    raid_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raid_instances.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    answer: Mapped[str] = mapped_column(String(120))
    correct: Mapped[bool]


class Wallet(TimestampMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("character_id", "currency"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id"), index=True)
    currency: Mapped[str] = mapped_column(String(32), default="embers")
    balance: Mapped[int] = mapped_column(default=0)


class LedgerEntry(TimestampMixin, Base):
    __tablename__ = "resource_ledger"
    __table_args__ = (UniqueConstraint("idempotency_key"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), index=True)
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    amount: Mapped[int]
    reason: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))


class OutboxEvent(TimestampMixin, Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_unpublished", "published_at", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[int] = mapped_column(default=1)
    producer: Mapped[str] = mapped_column(String(40), default="krada-api")
    subject_id: Mapped[str] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
