import pytest

from krada.modules.game.domain import CHARACTER_CLASSES, require_character_class
from krada.modules.raids.domain import RaidState, activate_new_raid, resolve_answer, transition


def test_all_initial_classes_are_registered():
    assert set(CHARACTER_CLASSES) == {"smith", "mage", "poet", "knight", "druid", "alchemist"}
    assert require_character_class("mage").title == "Волшебник"


def test_unknown_class_is_rejected():
    with pytest.raises(ValueError, match="unknown_character_class"):
        require_character_class("admin")


def test_raid_state_machine_rejects_skipping():
    with pytest.raises(ValueError, match="invalid_transition"):
        transition(RaidState.CREATED, RaidState.COMPLETED)
    assert transition(RaidState.ACTIVE, RaidState.COMPLETED) == RaidState.COMPLETED
    assert activate_new_raid() == RaidState.ACTIVE


def test_answer_reward_is_server_determined():
    win = resolve_answer(" 988 ", "988")
    loss = resolve_answer("862", "988")
    assert (win.correct, win.score, win.embers) == (True, 100, 15)
    assert (loss.correct, loss.score, loss.embers) == (False, 0, 3)
