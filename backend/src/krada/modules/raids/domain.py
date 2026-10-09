from dataclasses import dataclass
from enum import StrEnum


class RaidState(StrEnum):
    CREATED = "CREATED"
    LOBBY = "LOBBY"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS = {
    RaidState.CREATED: {RaidState.LOBBY, RaidState.CANCELLED},
    RaidState.LOBBY: {RaidState.ACTIVE, RaidState.CANCELLED},
    RaidState.ACTIVE: {RaidState.COMPLETED, RaidState.FAILED, RaidState.CANCELLED},
}


@dataclass(frozen=True)
class RaidResolution:
    correct: bool
    score: int
    xp: int
    embers: int


def transition(current: RaidState, target: RaidState) -> RaidState:
    """Apply an explicit raid state-machine transition."""
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid_transition:{current}:{target}")
    return target


def resolve_answer(answer: str, expected: str) -> RaidResolution:
    """Deterministically score a normalized answer; no client reward input is accepted."""
    correct = answer.strip().casefold() == expected.strip().casefold()
    return RaidResolution(
        correct=correct,
        score=100 if correct else 0,
        xp=40 if correct else 10,
        embers=15 if correct else 3,
    )
