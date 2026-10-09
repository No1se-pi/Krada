import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MockLoginIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)


class MaxLoginIn(BaseModel):
    init_data: str = Field(min_length=10, max_length=8192)


class SessionOut(BaseModel):
    access_token: str
    user_id: uuid.UUID
    school_id: uuid.UUID
    display_name: str


class CharacterIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
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
    answer: str = Field(min_length=1, max_length=120)


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
    display_name: str
    school_name: str
    class_name: str
    character: CharacterOut | None
    embers: int
    school_score: int
