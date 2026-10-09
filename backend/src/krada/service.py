import hashlib
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
from krada.modules.content.domain import require_question
from krada.modules.game.domain import require_character_class
from krada.modules.raids.domain import (
    RaidResolution,
    RaidState,
    activate_new_raid,
    resolve_answer,
    transition,
)

DEFAULT_QUESTION_KEY = "history-001"


def _operation_key(scope: str, raw_key: str) -> str:
    """Bind a client key to its actor and operation without storing the raw value.

    Client-generated UUIDs are not globally trustworthy. Hashing a server-built scope prevents
    one user's key from colliding with another user's reward or another endpoint's operation.
    """
    return hashlib.sha256(f"{scope}:{raw_key}".encode()).hexdigest()


def bootstrap_user(db: Session, display_name: str, provider: str, external_id: str) -> User:
    """Create or retrieve an identity and assign the MVP tenant on the server.

    This is intentionally the only pre-session flow that does not receive TenantContext: the
    verified external identity is what allows the server to discover the user's membership.
    """
    from krada.models import ExternalIdentity

    identity = db.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.provider == provider, ExternalIdentity.external_id == external_id
        )
    )
    if identity:
        user = db.get(User, identity.user_id)
        if not user:
            raise LookupError("identity_user_not_found")
        return user
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


def create_character(
    db: Session,
    principal: Principal,
    name: str,
    class_key: str,
    correlation_id: str,
) -> tuple[Character, bool]:
    """Create the actor's only character and its wallet atomically.

    The one-character-per-user constraint is the semantic idempotency boundary here. The caller
    still requires an Idempotency-Key so the contract can evolve without breaking clients.
    """
    require_character_class(class_key)
    school_id = principal.tenant.school_id
    existing = db.scalar(
        select(Character).where(
            Character.user_id == principal.user_id,
            Character.school_id == school_id,
        )
    )
    if existing:
        return existing, False
    character = Character(
        school_id=school_id,
        user_id=principal.user_id,
        name=name,
        class_key=class_key,
        visual_seed=random.SystemRandom().randint(1, 2**31),
    )
    db.add(character)
    try:
        # Flush early so uniqueness races are handled before dependent wallet/outbox rows exist.
        db.flush()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(
            select(Character).where(
                Character.user_id == principal.user_id,
                Character.school_id == school_id,
            )
        )
        if winner:
            return winner, False
        raise
    db.add(Wallet(school_id=school_id, character_id=character.id, currency="embers"))
    db.add(
        OutboxEvent(
            school_id=school_id,
            event_type="character.created",
            subject_id=str(character.id),
            correlation_id=correlation_id,
            payload={"class_key": class_key},
        )
    )
    db.commit()
    return character, True


def start_raid(
    db: Session,
    principal: Principal,
    character: Character,
    idempotency_key: str,
    correlation_id: str,
) -> tuple[Raid, bool]:
    """Start at most one active raid for a character.

    The database partial unique index is the final concurrency guard. The read-first path avoids
    exception-driven control flow for normal retries and restores the current raid after reconnect.
    """
    school_id = principal.tenant.school_id
    scoped_key = _operation_key(
        f"raid.start:{school_id}:{principal.user_id}:{character.id}", idempotency_key
    )
    existing = db.scalar(
        select(Raid).where(
            Raid.school_id == school_id,
            Raid.character_id == character.id,
            (Raid.idempotency_key == scoped_key) | (Raid.state == RaidState.ACTIVE),
        )
    )
    if existing:
        return existing, False
    raid = Raid(
        school_id=school_id,
        character_id=character.id,
        state=activate_new_raid(),
        question_key=DEFAULT_QUESTION_KEY,
        idempotency_key=scoped_key,
    )
    db.add(raid)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # A concurrent request may have won either the operation-key or active-raid constraint.
        winner = db.scalar(
            select(Raid).where(
                Raid.school_id == school_id,
                Raid.character_id == character.id,
                (Raid.idempotency_key == scoped_key) | (Raid.state == RaidState.ACTIVE),
            )
        )
        if winner:
            return winner, False
        raise
    db.add(
        OutboxEvent(
            school_id=school_id,
            event_type="raid.started",
            subject_id=str(raid.id),
            correlation_id=correlation_id,
            payload={"character_id": str(character.id)},
        )
    )
    db.commit()
    return raid, True


def complete_raid(
    db: Session,
    principal: Principal,
    raid_id: uuid.UUID,
    answer: str,
    idempotency_key: str,
    correlation_id: str,
) -> tuple[Raid, RaidResolution, int]:
    """Lock, resolve, reward, ledger, and outbox in one transaction.

    PostgreSQL row locks serialize competing answers. The unique attempt and scoped ledger key are
    independent backstops, so neither HTTP retries nor broker retries can mint a second reward.
    """
    school_id = principal.tenant.school_id
    scoped_key = _operation_key(
        f"raid.complete:{school_id}:{principal.user_id}:{raid_id}", idempotency_key
    )
    raid = db.scalar(
        select(Raid).where(Raid.id == raid_id, Raid.school_id == school_id).with_for_update()
    )
    if not raid:
        raise LookupError("raid_not_found")
    wallet = db.scalar(
        select(Wallet)
        .where(Wallet.character_id == raid.character_id, Wallet.school_id == school_id)
        .with_for_update()
    )
    if not wallet:
        raise LookupError("wallet_not_found")
    existing = db.scalar(
        select(LedgerEntry).where(
            LedgerEntry.school_id == school_id,
            LedgerEntry.wallet_id == wallet.id,
            LedgerEntry.idempotency_key == scoped_key,
        )
    )
    if existing:
        attempt = db.scalar(
            select(QuestionAttempt).where(
                QuestionAttempt.school_id == school_id,
                QuestionAttempt.raid_id == raid.id,
                QuestionAttempt.user_id == principal.user_id,
            )
        )
        if not attempt:
            raise RuntimeError("ledger_without_attempt")
        # Replay the exact historical outcome even if balance rules change in a later release.
        resolution = RaidResolution(
            correct=attempt.correct,
            score=attempt.score_awarded,
            xp=attempt.xp_awarded,
            embers=attempt.embers_awarded,
        )
        return raid, resolution, wallet.balance
    if RaidState(raid.state) != RaidState.ACTIVE:
        raise ValueError("raid_already_finished")
    question = require_question(raid.question_key)
    resolution = resolve_answer(answer, question.correct_answer)
    raid.state = transition(RaidState.ACTIVE, RaidState.COMPLETED)
    raid.score = resolution.score
    raid.completed_at = datetime.now(UTC)
    character = db.scalar(
        select(Character).where(
            Character.id == raid.character_id,
            Character.school_id == school_id,
        )
    )
    if not character:
        raise LookupError("character_not_found")
    character.xp += resolution.xp
    wallet.balance += resolution.embers
    db.add(
        QuestionAttempt(
            school_id=school_id,
            raid_id=raid.id,
            user_id=principal.user_id,
            answer=answer,
            correct=resolution.correct,
            score_awarded=resolution.score,
            xp_awarded=resolution.xp,
            embers_awarded=resolution.embers,
        )
    )
    db.add(
        LedgerEntry(
            school_id=school_id,
            wallet_id=wallet.id,
            amount=resolution.embers,
            reason="raid_completion",
            idempotency_key=scoped_key,
        )
    )
    db.add(
        OutboxEvent(
            school_id=school_id,
            event_type="raid.completed",
            subject_id=str(raid.id),
            correlation_id=correlation_id,
            payload={"score": resolution.score},
        )
    )
    db.add(
        OutboxEvent(
            school_id=school_id,
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
