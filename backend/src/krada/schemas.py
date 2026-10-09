import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
CharacterName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)
]
AnswerText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class MockLoginIn(BaseModel):
    display_name: DisplayName


class MaxLoginIn(BaseModel):
    init_data: str = Field(min_length=10, max_length=8192)


class SessionOut(BaseModel):
    access_token: str
    user_id: uuid.UUID
    school_id: uuid.UUID
    display_name: str


class CharacterIn(BaseModel):
    name: CharacterName
    class_key: Literal["smith", "mage", "poet", "knight", "druid", "alchemist"]


class CharacterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    class_key: str
    level: int
    xp: int
    visual_seed: int


class QuestionOut(BaseModel):
    id: str
    text: str
    options: list[str]
    subject: str


class RaidOut(BaseModel):
    id: uuid.UUID
    state: str
    score: int
    question: QuestionOut | None = None


class AnswerIn(BaseModel):
    answer: AnswerText


class RaidResultOut(BaseModel):
    raid_id: uuid.UUID
    state: str
    correct: bool
    explanation: str
    score: int
    xp_awarded: int
    embers_awarded: int
    embers_balance: int


class DashboardOut(BaseModel):
    """Reconnect-safe snapshot for the Mini App home screen."""

    display_name: str
    school_name: str
    class_name: str
    character: CharacterOut | None
    embers: int
    school_score: int
    # Returning the active raid lets a WebView recover after suspension or process restart.
    active_raid: RaidOut | None = None
