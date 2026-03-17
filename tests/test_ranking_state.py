from __future__ import annotations

import json
from pathlib import Path

from name_duel_game import ScoreTracker, save_ranking_state, load_ranking_state


def test_count_mode_state_roundtrip(tmp_path: Path) -> None:
    tracker = ScoreTracker(mode="count")
    tracker.record("Ada", "Bea")
    tracker.record("Ada", "Cara")
    tracker.record("Bea", "Cara")
    names = ["Ada", "Bea", "Cara"]
    state = tracker.to_state(names)
    assert state["mode"] == "count"
    ada_entry = next(item for item in state["entries"] if item["name"] == "Ada")
    assert ada_entry["wins"] == 2
    assert ada_entry["losses"] == 0
    assert ada_entry["matches"] == 2
    restored, restored_names = ScoreTracker.from_state(state)
    assert restored_names == names
    assert restored.entries["Bea"].wins == 1
    assert restored.entries["Bea"].losses == 1


def test_elo_mode_state_preserves_rating(tmp_path: Path) -> None:
    tracker = ScoreTracker(mode="elo")
    tracker.record("Anna", "Britta")
    tracker.record("Britta", "Cara")
    state = tracker.to_state(["Anna", "Britta", "Cara"])
    anna = next(item for item in state["entries"] if item["name"] == "Anna")
    assert anna["rating"] != 1000.0
    restored, _ = ScoreTracker.from_state(state)
    assert restored.entries["Anna"].wins == 1
    assert restored.entries["Anna"].rating == anna["rating"]


def test_save_and_load_state_file(tmp_path: Path) -> None:
    tracker = ScoreTracker(mode="count")
    tracker.record("A", "B")
    state_path = tmp_path / "state.json"
    names = ["A", "B", "C"]
    save_ranking_state(state_path, tracker, names)
    assert state_path.exists()
    with state_path.open(encoding="utf-8") as fh:
        saved = json.load(fh)
    assert saved["names"] == names
    loaded = load_ranking_state(state_path)
    assert loaded == saved
