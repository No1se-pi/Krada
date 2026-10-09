import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from krada.auth import Principal
from krada.database import Base
from krada.models import LedgerEntry, OutboxEvent
from krada.service import bootstrap_user, complete_raid, create_character, start_raid
from krada.tenancy import TenantContext


@pytest.fixture
def db():
    """Use a real unit of work without external infrastructure for domain integration."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def actor_for(user) -> Principal:
    return Principal(
        user_id=user.id,
        tenant=TenantContext(school_id=user.school_id),
        role=user.role,
    )


def test_vertical_flow_is_idempotent_and_replays_stored_reward(db: Session):
    user = bootstrap_user(db, "Добрыня", "test", "user-1")
    actor = actor_for(user)

    character, created = create_character(db, actor, "Ратибор", "mage", "request-1")
    same_character, created_again = create_character(db, actor, "Другое имя", "knight", "request-2")
    assert created is True
    assert created_again is False
    assert same_character.id == character.id

    raid, raid_created = start_raid(db, actor, character, "start-key", "request-3")
    same_raid, second_raid_created = start_raid(
        db, actor, character, "different-start-key", "request-4"
    )
    assert raid_created is True
    assert second_raid_created is False
    assert same_raid.id == raid.id

    completed, first_result, balance = complete_raid(
        db, actor, raid.id, "988", "answer-key", "request-5"
    )
    replayed, replay_result, replay_balance = complete_raid(
        db, actor, raid.id, "wrong-on-retry", "answer-key", "request-6"
    )

    assert completed.id == replayed.id
    assert first_result == replay_result
    assert (balance, replay_balance) == (15, 15)
    assert db.scalar(select(func.count()).select_from(LedgerEntry)) == 1
    assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 4


def test_tenant_cannot_complete_another_schools_raid(db: Session):
    owner = bootstrap_user(db, "Владелец", "test", "owner")
    owner_actor = actor_for(owner)
    character, _ = create_character(db, owner_actor, "Герой", "smith", "request-owner")
    raid, _ = start_raid(db, owner_actor, character, "start-owner", "request-raid")

    foreign_actor = Principal(
        user_id=uuid.uuid4(),
        tenant=TenantContext(school_id=uuid.uuid4()),
        role="student",
    )
    with pytest.raises(LookupError, match="raid_not_found"):
        complete_raid(db, foreign_actor, raid.id, "988", "foreign-key", "request-foreign")
