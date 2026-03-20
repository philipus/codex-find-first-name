from __future__ import annotations

import json
from pathlib import Path

from name_finder.analysis import bottom_entries, load_state, summarize_state, top_entries


def test_load_state_reads_json_object(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    payload = {
        "mode": "count",
        "names": ["Ada", "Bea"],
        "entries": [{"name": "Ada", "wins": 2, "losses": 0, "matches": 2, "score": 2}],
    }
    state_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_state(state_path)

    assert loaded == payload


def test_summarize_state_sorts_count_mode_with_inactive_names() -> None:
    payload = {
        "mode": "count",
        "names": ["Cara", "Ada", "Bea", "Dana"],
        "entries": [
            {"name": "Ada", "wins": 3, "losses": 1, "matches": 4, "score": 3},
            {"name": "Bea", "wins": 1, "losses": 2, "matches": 3, "score": 1},
            {"name": "Cara", "wins": 2, "losses": 1, "matches": 3, "score": 2},
        ],
    }

    summary = summarize_state(payload)

    assert [entry.name for entry in summary.ranking] == ["Ada", "Cara", "Bea", "Dana"]
    assert summary.metric_label == "score"
    assert summary.total_names == 4
    assert summary.total_comparisons == 5
    assert summary.ranking[-1].value == 0


def test_summarize_state_sorts_elo_mode_by_rating() -> None:
    payload = {
        "mode": "elo",
        "names": ["Ada", "Bea", "Cara"],
        "entries": [
            {"name": "Ada", "wins": 3, "losses": 1, "matches": 4, "rating": 1042.5},
            {"name": "Bea", "wins": 1, "losses": 2, "matches": 3, "rating": 991.25},
            {"name": "Cara", "wins": 0, "losses": 1, "matches": 1, "rating": 980.0},
        ],
    }

    summary = summarize_state(payload)

    assert [entry.name for entry in summary.ranking] == ["Ada", "Bea", "Cara"]
    assert summary.metric_label == "rating"
    assert summary.total_comparisons == 4


def test_top_and_bottom_entries_use_requested_limit() -> None:
    payload = {
        "mode": "count",
        "names": ["Ada", "Bea", "Cara", "Dana", "Elle"],
        "entries": [
            {"name": "Ada", "wins": 5, "losses": 0, "matches": 5, "score": 5},
            {"name": "Bea", "wins": 4, "losses": 1, "matches": 5, "score": 4},
            {"name": "Cara", "wins": 3, "losses": 2, "matches": 5, "score": 3},
            {"name": "Dana", "wins": 1, "losses": 4, "matches": 5, "score": 1},
            {"name": "Elle", "wins": 0, "losses": 5, "matches": 5, "score": 0},
        ],
    }

    summary = summarize_state(payload)

    assert [entry.name for entry in top_entries(summary, limit=2)] == ["Ada", "Bea"]
    assert [entry.name for entry in bottom_entries(summary, limit=2)] == ["Elle", "Dana"]
