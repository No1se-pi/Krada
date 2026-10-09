import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from krada.auth import Principal, current_principal, issue_token, validate_max_init_data
from krada.config import Settings, get_settings
from krada.database import get_db
from krada.models import Character, Raid, School, SchoolClass, User, Wallet
from krada.schemas import (
    AnswerIn,
    CharacterIn,
    CharacterOut,
    DashboardOut,
    MaxLoginIn,
    MockLoginIn,
    QuestionOut,
    RaidOut,
    RaidResultOut,
    SessionOut,
)
from krada.service import QUESTION, bootstrap_user, complete_raid, create_character, start_raid

router = APIRouter(prefix="/api/v1")


def session_for(user: User, settings: Settings) -> SessionOut:
    return SessionOut(
        access_token=issue_token(user.id, user.school_id, user.role, settings),
        user_id=user.id,
        school_id=user.school_id,
        display_name=user.display_name,
    )


@router.post("/auth/mock", response_model=SessionOut)
def mock_login(
    data: MockLoginIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> SessionOut:
    if settings.app_env != "local" or not settings.allow_mock_auth:
        raise HTTPException(404, "Not found")
    stable_id = uuid.uuid5(uuid.NAMESPACE_URL, data.display_name.strip().casefold()).hex
    return session_for(bootstrap_user(db, data.display_name, "mock", stable_id), settings)


@router.post("/auth/max", response_model=SessionOut)
def max_login(
    data: MaxLoginIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> SessionOut:
    try:
        parsed = validate_max_init_data(data.init_data, settings.max_bot_token)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            401, detail={"code": "invalid_max_data", "message": "Не удалось подтвердить запуск MAX"}
        ) from exc
    max_user = parsed["user"]
    display_name = (
        " ".join(filter(None, [max_user.get("first_name"), max_user.get("last_name")]))
        or "Странник"
    )
    return session_for(bootstrap_user(db, display_name, "max", str(max_user["id"])), settings)


@router.get("/me", response_model=DashboardOut)
def dashboard(
    principal: Principal = Depends(current_principal), db: Session = Depends(get_db)
) -> DashboardOut:
    user = db.scalar(
        select(User).where(User.id == principal.user_id, User.school_id == principal.school_id)
    )
    if not user:
        raise HTTPException(404, "User not found")
    character = db.scalar(
        select(Character).where(
            Character.user_id == user.id, Character.school_id == principal.school_id
        )
    )
    wallet = (
        db.scalar(
            select(Wallet).where(
                Wallet.character_id == character.id, Wallet.school_id == principal.school_id
            )
        )
        if character
        else None
    )
    school_score = (
        db.scalar(
            select(func.coalesce(func.sum(Raid.score), 0)).where(
                Raid.school_id == principal.school_id
            )
        )
        or 0
    )
    return DashboardOut(
        display_name=user.display_name,
        school_name=db.get(School, user.school_id).name,
        class_name=db.get(SchoolClass, user.class_id).name,
        character=CharacterOut.model_validate(character) if character else None,
        embers=wallet.balance if wallet else 0,
        school_score=school_score,
    )


@router.get("/character-classes")
def list_classes() -> list[dict]:
    from krada.modules.game.domain import CHARACTER_CLASSES

    return [
        {"key": item.key, "title": item.title, "description": item.description, "stats": item.stats}
        for item in CHARACTER_CLASSES.values()
    ]


@router.post("/characters", response_model=CharacterOut, status_code=201)
def new_character(
    data: CharacterIn,
    response: Response,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> Character:
    existing = db.scalar(
        select(Character).where(
            Character.user_id == principal.user_id, Character.school_id == principal.school_id
        )
    )
    if existing:
        response.status_code = 200
        return existing
    return create_character(db, principal, data.name, data.class_key)


@router.post("/raids", response_model=RaidOut, status_code=201)
def new_raid(
    x_request_id: str | None = Header(None),
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> RaidOut:
    character = db.scalar(
        select(Character).where(
            Character.user_id == principal.user_id, Character.school_id == principal.school_id
        )
    )
    if not character:
        raise HTTPException(
            409, detail={"code": "character_required", "message": "Сначала создайте героя"}
        )
    raid = start_raid(db, principal, character, x_request_id or str(uuid.uuid4()))
    return RaidOut(id=raid.id, state=raid.state, score=raid.score, question=QuestionOut(**QUESTION))


@router.get("/raids/{raid_id}", response_model=RaidOut)
def get_raid(
    raid_id: uuid.UUID,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> RaidOut:
    raid = db.scalar(select(Raid).where(Raid.id == raid_id, Raid.school_id == principal.school_id))
    if not raid:
        raise HTTPException(404, "Raid not found")
    question = QuestionOut(**QUESTION) if raid.state == "ACTIVE" else None
    return RaidOut(id=raid.id, state=raid.state, score=raid.score, question=question)


@router.post("/raids/{raid_id}/answer", response_model=RaidResultOut)
def answer_raid(
    raid_id: uuid.UUID,
    data: AnswerIn,
    idempotency_key: str = Header(min_length=8, max_length=128),
    x_request_id: str | None = Header(None),
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> RaidResultOut:
    try:
        raid, result, balance = complete_raid(
            db, principal, raid_id, data.answer, idempotency_key, x_request_id or str(uuid.uuid4())
        )
    except LookupError as exc:
        raise HTTPException(404, "Raid not found") from exc
    except ValueError as exc:
        raise HTTPException(
            409, detail={"code": str(exc), "message": "Операция уже завершена"}
        ) from exc
    return RaidResultOut(
        raid_id=raid.id,
        state=raid.state,
        correct=result.correct,
        explanation="Крещение Руси произошло в 988 году.",
        score=result.score,
        xp_awarded=result.xp,
        embers_awarded=result.embers,
        embers_balance=balance,
    )


@router.get("/leaderboards/schools")
def leaderboard(
    principal: Principal = Depends(current_principal), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.execute(
        select(School.id, School.name, func.coalesce(func.sum(Raid.score), 0).label("score"))
        .outerjoin(Raid, Raid.school_id == School.id)
        .group_by(School.id)
        .order_by(func.sum(Raid.score).desc())
        .limit(20)
    ).all()
    return [
        {
            "rank": index,
            "school": name,
            "score": score,
            "is_current": school_id == principal.school_id,
        }
        for index, (school_id, name, score) in enumerate(rows, 1)
    ]
