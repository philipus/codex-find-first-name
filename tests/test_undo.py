from __future__ import annotations

from name_finder.name_duel_game import (
    ScoreTracker,
    capture_duel_snapshot,
    restore_duel_snapshot,
)


def test_undo_restores_simple_counts() -> None:
    tracker = ScoreTracker(mode="count")
    pair = ("Ada", "Bea")
    snapshot = capture_duel_snapshot(tracker, pair, autosave_counter=4)
    tracker.record("Ada", "Bea")
    assert tracker.entries["Ada"].wins == 1
    restored_counter = restore_duel_snapshot(tracker, snapshot)
    assert restored_counter == 4
    assert "Ada" not in tracker.entries
    assert "Bea" not in tracker.entries


def test_undo_restores_elo_ratings() -> None:
    tracker = ScoreTracker(mode="elo")
    tracker.record("Ava", "Bea")
    pre_rating = tracker.entries["Ava"].rating
    pair = ("Ava", "Cara")
    snapshot = capture_duel_snapshot(tracker, pair, autosave_counter=0)
    tracker.record("Ava", "Cara")
    assert tracker.entries["Ava"].rating != pre_rating
    restored_counter = restore_duel_snapshot(tracker, snapshot)
    assert restored_counter == 0
    assert tracker.entries["Ava"].rating == pre_rating
    assert "Cara" not in tracker.entries
