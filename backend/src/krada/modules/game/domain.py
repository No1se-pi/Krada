from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class CharacterClass:
    key: str
    title: str
    description: str
    stats: dict[str, int]


_CLASSES = {
    item.key: item
    for item in (
        CharacterClass("smith", "Кузнец", "Создаёт и улучшает", {"endurance": 3, "focus": 2}),
        CharacterClass(
            "mage", "Волшебник", "Превращает знания в силу", {"intellect": 3, "energy": 2}
        ),
        CharacterClass("poet", "Поэт", "Управляет словами", {"charisma": 3, "focus": 2}),
        CharacterClass("knight", "Рыцарь", "Защищает союзников", {"endurance": 3, "energy": 2}),
        CharacterClass(
            "druid", "Друид", "Поддерживает и восстанавливает", {"focus": 3, "energy": 2}
        ),
        CharacterClass("alchemist", "Алхимик", "Комбинирует ресурсы", {"intellect": 2, "focus": 3}),
    )
}
CHARACTER_CLASSES = MappingProxyType(_CLASSES)


def require_character_class(key: str) -> CharacterClass:
    """Return configured class or reject an unknown client value."""
    try:
        return CHARACTER_CLASSES[key]
    except KeyError as exc:
        raise ValueError("unknown_character_class") from exc
