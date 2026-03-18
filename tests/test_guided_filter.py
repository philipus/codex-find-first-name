from __future__ import annotations

import json
from pathlib import Path

from name_finder.name_duel_game import (
    guided_filter_names,
    select_records_for_names,
    save_filtered_records,
)


def test_guided_filter_names_honors_choices() -> None:
    names = ["Ada", "Bea", "Cara", "Dana"]
    responses = iter(["y", "n", "q"])
    captured: list[str] = []

    def fake_prompt(_: str) -> str:
        return next(responses)

    def fake_notify(message: str) -> None:
        captured.append(message)

    result = guided_filter_names(names, prompt=fake_prompt, notify=fake_notify)
    assert result == ["Ada", "Cara", "Dana"]
    assert any("Excluded 'Bea'" in line for line in captured)
    assert any("Stopping guided filtering" in line for line in captured)


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
