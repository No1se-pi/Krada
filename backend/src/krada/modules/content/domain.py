from dataclasses import dataclass
from types import MappingProxyType
from typing import TypedDict


class PublicQuestion(TypedDict):
    """Explicit allow-list for a question before evaluation."""

    id: str
    text: str
    options: list[str]
    subject: str


@dataclass(frozen=True, slots=True)
class QuestionDefinition:
    """Versioned server-side question definition.

    `correct_answer` must never be serialized directly. API code receives only `public_view()`;
    evaluation remains inside the trusted application boundary.
    """

    key: str
    text: str
    options: tuple[str, ...]
    subject: str
    correct_answer: str
    explanation: str

    def public_view(self) -> PublicQuestion:
        """Return the allow-listed fields that are safe before an attempt is submitted."""
        return {
            "id": self.key,
            "text": self.text,
            "options": list(self.options),
            "subject": self.subject,
        }


_QUESTIONS = {
    "history-001": QuestionDefinition(
        key="history-001",
        text="В каком году произошло Крещение Руси?",
        options=("862", "988", "1240", "1380"),
        subject="История",
        correct_answer="988",
        explanation="Крещение Руси произошло в 988 году.",
    )
}
QUESTIONS = MappingProxyType(_QUESTIONS)


def require_question(key: str) -> QuestionDefinition:
    """Resolve a trusted catalog key without accepting arbitrary executable content."""
    try:
        return QUESTIONS[key]
    except KeyError as exc:
        raise ValueError("unknown_question") from exc
