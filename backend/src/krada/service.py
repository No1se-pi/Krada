import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from krada.auth import Principal
from krada.models import (
    Character,
    LedgerEntry,
    OutboxEvent,
    QuestionAttempt,
    Raid,
    School,
    SchoolClass,
    User,
    Wallet,
)
from krada.modules.game.domain import require_character_class
from krada.modules.raids.domain import RaidState, resolve_answer, transition

QUESTION = {
    "id": "history-001",
    "text": "В каком году произошло Крещение Руси?",
    "options": ["862", "988", "1240", "1380"],
    "subject": "История",
}
EXPECTED_ANSWER = "988"


def bootstrap_user(db: Session, display_name: str, provider: str, external_id: str) -> User:
    """Create or retrieve a demo-tenant user; membership is assigned server-side."""
    from krada.models import ExternalIdentity

    identity = db.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.provider == provider, ExternalIdentity.external_id == external_id
        )
    )
    if identity:
        return db.get(User, identity.user_id)  # type: ignore[return-value]
    school = db.scalar(select(School).where(School.name == "Школа Бересты"))
    if not school:
        school = School(name="Школа Бересты")
        db.add(school)
        db.flush()
    school_class = db.scalar(
        select(SchoolClass).where(SchoolClass.school_id == school.id, SchoolClass.name == "7А")
    )
    if not school_class:
        school_class = SchoolClass(school_id=school.id, name="7А")
        db.add(school_class)
        db.flush()
    user = User(school_id=school.id, class_id=school_class.id, display_name=display_name)
    db.add(user)
    db.flush()
    db.add(ExternalIdentity(user_id=user.id, provider=provider, external_id=external_id))
    db.commit()
    return user


def create_character(db: Session, principal: Principal, name: str, class_key: str) -> Character:
    require_character_class(class_key)
    existing = db.scalar(
        select(Character).where(
            Character.user_id == principal.user_id, Character.school_id == principal.school_id
        )
    )
    if existing:
        return existing
    character = Character(
        school_id=principal.school_id,
        user_id=principal.user_id,
        name=name,
        class_key=class_key,
        visual_seed=random.SystemRandom().randint(1, 2**31),
    )
    db.add(character)
    db.flush()
    db.add(Wallet(school_id=principal.school_id, character_id=character.id, currency="embers"))
    db.add(
        OutboxEvent(
            school_id=principal.school_id,
            event_type="character.created",
            subject_id=str(character.id),
            correlation_id=str(uuid.uuid4()),
            payload={"class_key": class_key},
        )
    )
    db.commit()
    return character


def start_raid(
    db: Session, principal: Principal, character: Character, correlation_id: str
) -> Raid:
    raid = Raid(
        school_id=principal.school_id,
        character_id=character.id,
        state=RaidState.ACTIVE,
        question_key=QUESTION["id"],
    )
    db.add(raid)
    db.flush()
    db.add(
        OutboxEvent(
            school_id=principal.school_id,
            event_type="raid.started",
            subject_id=str(raid.id),
            correlation_id=correlation_id,
            payload={"character_id": str(character.id)},
        )
    )
    db.commit()
    return raid


def complete_raid(
    db: Session,
    principal: Principal,
    raid_id: uuid.UUID,
    answer: str,
    idempotency_key: str,
    correlation_id: str,
) -> tuple[Raid, object, int]:
    """Lock, resolve, reward, ledger, and outbox atomically."""
    existing = db.scalar(select(LedgerEntry).where(LedgerEntry.idempotency_key == idempotency_key))
    raid = db.scalar(
        select(Raid)
        .where(Raid.id == raid_id, Raid.school_id == principal.school_id)
        .with_for_update()
    )
    if not raid:
        raise LookupError("raid_not_found")
    wallet = db.scalar(
        select(Wallet)
        .where(Wallet.character_id == raid.character_id, Wallet.school_id == principal.school_id)
        .with_for_update()
    )
    if existing:
        attempt = db.scalar(
            select(QuestionAttempt).where(
                QuestionAttempt.raid_id == raid.id,
                QuestionAttempt.user_id == principal.user_id,
            )
        )
        # Rebuild the original result, never from a potentially changed retry body.
        canonical_answer = EXPECTED_ANSWER if attempt and attempt.correct else ""
        resolution = resolve_answer(canonical_answer, EXPECTED_ANSWER)
        return raid, resolution, wallet.balance  # type: ignore[union-attr]
    if RaidState(raid.state) != RaidState.ACTIVE:
        raise ValueError("raid_already_finished")
    resolution = resolve_answer(answer, EXPECTED_ANSWER)
    raid.state = transition(RaidState.ACTIVE, RaidState.COMPLETED)
    raid.score = resolution.score
    raid.completed_at = datetime.now(UTC)
    character = db.get(Character, raid.character_id)
    character.xp += resolution.xp  # type: ignore[union-attr]
    wallet.balance += resolution.embers  # type: ignore[union-attr]
    db.add(
        QuestionAttempt(
            school_id=principal.school_id,
            raid_id=raid.id,
            user_id=principal.user_id,
            answer=answer,
            correct=resolution.correct,
        )
    )
    db.add(
        LedgerEntry(
            school_id=principal.school_id,
            wallet_id=wallet.id,
            amount=resolution.embers,
            reason="raid_completion",
            idempotency_key=idempotency_key,
        )
    )
    db.add(
        OutboxEvent(
            school_id=principal.school_id,
            event_type="raid.completed",
            subject_id=str(raid.id),
            correlation_id=correlation_id,
            payload={"score": resolution.score},
        )
    )
    db.add(
        OutboxEvent(
            school_id=principal.school_id,
            event_type="reward.granted",
            subject_id=str(wallet.id),
            correlation_id=correlation_id,
            payload={"currency": "embers", "amount": resolution.embers},
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("duplicate_operation") from None
    return raid, resolution, wallet.balance
