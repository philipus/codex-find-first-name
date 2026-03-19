from __future__ import annotations

import json
from pathlib import Path

from name_finder.name_duel_game import (
    guided_filter_names,
    save_filtered_records,
    select_records_for_names,
)


def run_guided_filter(names: list[str], responses: list[str]) -> tuple[list[str], list[str], list[str]]:
    reply_iter = iter(responses)
    prompts: list[str] = []
    notifications: list[str] = []

    def fake_prompt(message: str) -> str:
        prompts.append(message)
        return next(reply_iter)

    def fake_notify(message: str) -> None:
        notifications.append(message)

    result = guided_filter_names(names, prompt=fake_prompt, notify=fake_notify)
    return result, prompts, notifications


def test_guided_filter_names_honors_choices() -> None:
    names = ["Ada", "Bea", "Cara", "Dana"]

    result, _, captured = run_guided_filter(names, ["y", "n", "q"])

    assert result == ["Ada", "Cara", "Dana"]
    assert any("Excluded 'Bea'" in line for line in captured)
    assert any("Stopping guided filtering" in line for line in captured)


def test_guided_filter_undo_after_keep_replays_same_name() -> None:
    result, prompts, notifications = run_guided_filter(["Ada", "Bea"], ["y", "u", "n", "q"])

    assert result == ["Bea"]
    assert prompts[:3] == [
        "[1/2] Keep 'Ada'? [y/n/u/q]: ",
        "[2/2] Keep 'Bea'? [y/n/u/q]: ",
        "[1/2] Keep 'Ada'? [y/n/u/q]: ",
    ]
    assert any("Last guided-filtering decision undone." in line for line in notifications)


def test_guided_filter_undo_after_exclude_restores_state() -> None:
    result, prompts, notifications = run_guided_filter(["Ada", "Bea"], ["n", "u", "y", "q"])

    assert result == ["Ada", "Bea"]
    assert prompts[:3] == [
        "[1/2] Keep 'Ada'? [y/n/u/q]: ",
        "[2/2] Keep 'Bea'? [y/n/u/q]: ",
        "[1/2] Keep 'Ada'? [y/n/u/q]: ",
    ]
    assert any("Excluded 'Ada'" in line for line in notifications)
    assert any("Last guided-filtering decision undone." in line for line in notifications)


def test_guided_filter_undo_with_no_previous_decision_is_graceful() -> None:
    result, prompts, notifications = run_guided_filter(["Ada", "Bea"], ["u", "y", "q"])

    assert result == ["Ada", "Bea"]
    assert prompts[:2] == [
        "[1/2] Keep 'Ada'? [y/n/u/q]: ",
        "[1/2] Keep 'Ada'? [y/n/u/q]: ",
    ]
    assert any("Nothing to undo during guided filtering." in line for line in notifications)


def test_guided_filter_continues_after_undo_with_different_choice() -> None:
    result, prompts, notifications = run_guided_filter(["Ada", "Bea", "Cara"], ["y", "u", "n", "y", "q"])

    assert result == ["Bea", "Cara"]
    assert prompts[:4] == [
        "[1/3] Keep 'Ada'? [y/n/u/q]: ",
        "[2/3] Keep 'Bea'? [y/n/u/q]: ",
        "[1/3] Keep 'Ada'? [y/n/u/q]: ",
        "[2/3] Keep 'Bea'? [y/n/u/q]: ",
    ]
    assert any("Last guided-filtering decision undone." in line for line in notifications)


def test_save_filtered_records_structure(tmp_path: Path) -> None:
    records = [
        {"name": "Ada", "gender": "female", "source": "src-a"},
        {"name": "Ada", "gender": "male", "source": "src-b"},
        {"name": "Bea", "gender": "female", "source": "src-c"},
    ]
    allowed = {"Ada", "Bea"}
    filtered = select_records_for_names(records, allowed, gender="female")
    assert filtered == [records[0], records[2]]
    output = tmp_path / "filtered.json"
    save_filtered_records(filtered, output)
    with output.open(encoding="utf-8") as fh:
        saved = json.load(fh)
    assert saved == filtered
