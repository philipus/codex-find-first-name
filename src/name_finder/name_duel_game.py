#!/usr/bin/env python3
"""Simple CLI pairwise ranking game for baby names."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

from name_finder.analysis import format_analysis, load_state, summarize_state

DATA_PATH = Path("data") / "all_names.json"


def load_names(path: Path, gender: str | None = None) -> List[str]:
    """Load unique names from the JSON dataset."""
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}. Run the scraper first.")
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    seen = set()
    names: List[str] = []
    gender_filter = gender.lower() if gender else None
    for entry in payload:
        if gender_filter:
            entry_gender = entry.get("gender", "").lower()
            if entry_gender != gender_filter:
                continue
        name = entry.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    if len(names) < 2:
        raise ValueError("Need at least two unique names to play.")
    return names


@dataclass
class ScoreEntry:
    wins: int = 0
    losses: int = 0
    rating: float = 1000.0


class ScoreTracker:
    """Keeps score per name with optional Elo-style updates."""

    def __init__(self, mode: str = "count", k_factor: float = 32.0) -> None:
        self.mode = mode
        self.k_factor = k_factor
        self.entries: Dict[str, ScoreEntry] = {}

    def _get_entry(self, name: str) -> ScoreEntry:
        if name not in self.entries:
            self.entries[name] = ScoreEntry()
        return self.entries[name]

    def record(self, winner: str, loser: str) -> None:
        win_entry = self._get_entry(winner)
        lose_entry = self._get_entry(loser)
        win_entry.wins += 1
        lose_entry.losses += 1

        if self.mode == "elo":
            self._apply_elo(win_entry, lose_entry)
        else:
            # Default mode simply counts wins; nothing else to update.
            pass

    def _apply_elo(self, winner_entry: ScoreEntry, loser_entry: ScoreEntry) -> None:
        expected_win = self._expected_score(winner_entry.rating, loser_entry.rating)
        expected_loss = self._expected_score(loser_entry.rating, winner_entry.rating)
        winner_entry.rating += self.k_factor * (1 - expected_win)
        loser_entry.rating += self.k_factor * (0 - expected_loss)

    @staticmethod
    def _expected_score(rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))

    def ranking(self) -> List[Tuple[str, ScoreEntry]]:
        return sorted(
            self.entries.items(),
            key=lambda item: self._score_value(item[1]),
            reverse=True,
        )

    def _score_value(self, entry: ScoreEntry) -> float:
        return entry.rating if self.mode == "elo" else float(entry.wins)

    def to_state(self, names: Sequence[str]) -> dict:
        name_set = set(names)
        entries = []
        for name in names:
            if name in self.entries:
                entries.append(self._entry_state(name, self.entries[name]))
        for name, entry in self.entries.items():
            if name not in name_set:
                entries.append(self._entry_state(name, entry))
        return {"mode": self.mode, "names": list(names), "entries": entries}

    def _entry_state(self, name: str, entry: ScoreEntry) -> dict:
        matches = entry.wins + entry.losses
        score = self._score_value(entry)
        return {
            "name": name,
            "wins": entry.wins,
            "losses": entry.losses,
            "matches": matches,
            "rating": entry.rating,
            "score": score,
        }

    @classmethod
    def from_state(cls, payload: dict) -> Tuple["ScoreTracker", List[str]]:
        mode = payload.get("mode", "count")
        tracker = cls(mode=mode)
        for entry_payload in payload.get("entries", []):
            name = entry_payload.get("name")
            if not name:
                continue
            entry = tracker._get_entry(name)
            entry.wins = int(entry_payload.get("wins", 0))
            entry.losses = int(entry_payload.get("losses", 0))
            entry.rating = float(entry_payload.get("rating", entry.rating))
        names = payload.get("names", [])
        return tracker, list(names)


def pick_pair(names: List[str], rng: random.Random) -> Tuple[str, str]:
    first, second = rng.sample(names, 2)
    return first, second


def run_game(
    names: Iterable[str],
    mode: str,
    seed: int | None = None,
    tracker: ScoreTracker | None = None,
    state_path: Path | None = None,
    autosave_interval: int = 0,
) -> None:
    rng = random.Random(seed)
    tracker = tracker or ScoreTracker(mode=mode)
    names_list = list(names)
    autosave_counter = 0
    history: List[dict] = []
    pending_pair: Tuple[str, str] | None = None

    print("Pairwise Name Duel")
    print("-------------------")
    print("Choose your favorite between two names.")
    print("Controls: 1 = first, 2 = second, s = skip, u = undo last, q = quit.")
    print()

    while True:
        if pending_pair is not None:
            first, second = pending_pair
            pending_pair = None
        else:
            first, second = pick_pair(names_list, rng)
        print(f"1) {first}")
        print(f"2) {second}")
        choice = input("Your pick [1/2/s/u/q]: ").strip().lower()
        if choice == "q":
            break
        if choice == "s":
            print("Skipped.\n")
            continue
        if choice == "u":
            if not history:
                print("Nothing to undo.\n")
                continue
            snapshot = history.pop()
            pending_pair = snapshot["pair"]
            autosave_counter = restore_duel_snapshot(tracker, snapshot)
            if state_path:
                save_ranking_state(state_path, tracker, names_list)
                print(f"[Undo saved to {state_path}]")
            print("Last decision undone.\n")
            continue
        if choice == "1":
            snapshot = capture_duel_snapshot(tracker, (first, second), autosave_counter)
            tracker.record(first, second)
            print(f"You preferred {first}.\n")
            autosave_counter += 1
            history.append(snapshot)
        elif choice == "2":
            snapshot = capture_duel_snapshot(tracker, (first, second), autosave_counter)
            tracker.record(second, first)
            print(f"You preferred {second}.\n")
            autosave_counter += 1
            history.append(snapshot)
        else:
            print("Invalid input, try again.\n")
            continue

        if autosave_interval > 0 and autosave_counter >= autosave_interval:
            save_ranking_state(state_path, tracker, names_list)
            autosave_counter = 0
            print(f"[Autosaved ranking progress to {state_path}]")

    print("\nResults")
    print("-------")
    ranking = tracker.ranking()
    if not ranking:
        print("No results recorded. Play at least one round next time!")
        save_ranking_state(state_path, tracker, names_list)
        if state_path:
            print(f"Progress saved to {state_path}")
        return
    for idx, (name, entry) in enumerate(ranking, start=1):
        total_matches = entry.wins + entry.losses
        score_val = entry.rating if mode == "elo" else entry.wins
        metric_label = "rating" if mode == "elo" else "wins"
        score_str = f"{score_val:.2f}" if mode == "elo" else str(int(score_val))
        print(
            f"{idx:>3}. {name:<20} {metric_label}: {score_str} "
            f"(wins: {entry.wins}, losses: {entry.losses}, matches: {total_matches})"
        )

    save_ranking_state(state_path, tracker, names_list)
    if state_path:
        print(f"Final ranking saved to {state_path}")


def perform_setup(names: List[str], mode: str, rng: random.Random) -> List[str]:
    total_names = len(names)
    mode_label = "elo" if mode == "elo" else "simple"
    print("Setup")
    print("-----")
    print(f"Names available: {total_names}")
    print(f"Scoring mode: {mode_label}")
    full_pairs = (total_names * (total_names - 1)) // 2
    print(f"Full pairwise comparisons: {full_pairs}")
    if mode == "elo":
        print("Elo useful ranking: ~3n-5n comparisons; stable: ~5n-8n.")
    else:
        print("Simple scoring useful ranking: ~5n-10n comparisons.")
    print("The game samples random pairs instead of enumerating them all.")
    comparisons = prompt_comparison_budget(total_names, mode)
    recommended = recommend_name_count(mode, comparisons)
    recommended = max(2, min(total_names, recommended))
    print(f"Recommended number of names for your budget: {recommended}")
    if total_names <= recommended:
        print("Using all available names.\n")
        return names
    choice = prompt_selection_choice()
    if choice == "1":
        print("Using all names as requested.\n")
        return names
    if choice == "2":
        reduced = random_reduce(names, recommended, rng)
        print(f"Randomly reduced to {len(reduced)} names.\n")
        return reduced
    reduced = manual_exclude(names)
    if len(reduced) < 2:
        raise RuntimeError("Need at least two names after manual exclusion.")
    print(f"Manual selection complete. {len(reduced)} names remain.\n")
    return reduced


def prompt_comparison_budget(total_names: int, mode: str) -> int:
    if mode == "elo":
        prompt = (
            f"How many comparisons will you make? "
            f"(Elo guidance: 3n-5n useful, 5n-8n stable) [default {4 * total_names}]: "
        )
        suggested = 4 * total_names
    else:
        prompt = (
            f"How many comparisons will you make? "
            f"(Simple guidance: 5n-10n) [default {7 * total_names}]: "
        )
        suggested = 7 * total_names
    default_value = suggested if total_names > 0 else 10
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default_value
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("Please enter a positive integer.")


def recommend_name_count(mode: str, comparisons: int) -> int:
    divisor = 4 if mode == "elo" else 7
    return max(2, comparisons // divisor)


def prompt_selection_choice() -> str:
    print("Your name list exceeds the recommended size.")
    print("Options:")
    print("  1) Use all names anyway")
    print("  2) Randomly reduce to the recommended count")
    print("  3) Manually exclude specific names")
    while True:
        choice = input("Select an option [1/2/3]: ").strip()
        if choice in {"1", "2", "3"}:
            return choice
        print("Please enter 1, 2, or 3.")


def random_reduce(names: Sequence[str], target: int, rng: random.Random) -> List[str]:
    if target >= len(names):
        return list(names)
    return rng.sample(list(names), target)


def manual_exclude(names: List[str]) -> List[str]:
    remaining = list(names)
    print("Manual exclusion selected. Enter names to remove (comma-separated).")
    print("Press Enter on an empty line when you are done.")
    while True:
        print(f"{len(remaining)} names remain.")
        preview = ", ".join(remaining[: min(10, len(remaining))])
        if preview:
            print(f"Sample names: {preview}")
        entry = input("Names to remove: ").strip()
        if not entry:
            break
        tokens = [token.strip() for token in entry.split(",") if token.strip()]
        removed_any = False
        for token in tokens:
            match = next((name for name in remaining if name.lower() == token.lower()), None)
            if match:
                remaining.remove(match)
                removed_any = True
                print(f"Removed {match}.")
            else:
                print(f"Name '{token}' not found; skipping.")
        if not removed_any:
            print("No names removed in this step.")
        if len(remaining) < 2:
            print("Reached the minimum of 2 names.")
            break
    return remaining


def load_dataset_records(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}. Run the scraper first.")
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a list of name records.")
    return data


def prompt_yes_no(question: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        reply = input(question + suffix).strip().lower()
        if not reply:
            return default
        if reply in {"y", "yes"}:
            return True
        if reply in {"n", "no"}:
            return False
        print("Please answer with 'y' or 'n'.")


def capture_guided_filter_snapshot(kept: Sequence[str], index: int) -> dict:
    return {"kept_count": len(kept), "index": index}


def restore_guided_filter_snapshot(kept: List[str], snapshot: dict) -> int:
    kept_count = int(snapshot.get("kept_count", 0))
    del kept[kept_count:]
    return int(snapshot.get("index", 0))


def guided_filter_names(
    names: Sequence[str],
    prompt: Callable[[str], str] = input,
    notify: Callable[[str], None] = print,
) -> List[str]:
    kept: List[str] = []
    history: List[dict] = []
    total = len(names)
    if total == 0:
        return kept
    notify("Guided filtering controls: y = keep, n = discard, u = undo last, q = finish reviewing.\n")
    idx = 0
    while idx < total:
        name = names[idx]
        response = prompt(f"[{idx + 1}/{total}] Keep '{name}'? [y/n/u/q]: ").strip().lower()
        if response == "y":
            history.append(capture_guided_filter_snapshot(kept, idx))
            kept.append(name)
            idx += 1
            notify(f"Kept {len(kept)} of {idx} reviewed.\n")
            continue
        if response == "n":
            history.append(capture_guided_filter_snapshot(kept, idx))
            idx += 1
            notify(f"Excluded '{name}'. {len(kept)} kept so far.\n")
            continue
        if response == "u":
            if not history:
                notify("Nothing to undo during guided filtering.\n")
                continue
            idx = restore_guided_filter_snapshot(kept, history.pop())
            notify("Last guided-filtering decision undone.\n")
            continue
        if response == "q":
            notify("Stopping guided filtering; remaining names are kept.")
            kept.extend(names[idx:])
            return kept
        notify("Please enter 'y', 'n', 'u', or 'q'.")
    return kept


def select_records_for_names(
    records: List[dict],
    allowed_names: Iterable[str],
    gender: str | None = None,
) -> List[dict]:
    allowed = {name.lower() for name in allowed_names}
    gender_filter = gender.lower() if gender else None
    selected: List[dict] = []
    for record in records:
        name = str(record.get("name", "")).lower()
        if name not in allowed:
            continue
        if gender_filter and str(record.get("gender", "")).lower() != gender_filter:
            continue
        selected.append(record)
    return selected


def save_filtered_records(records: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def maybe_guided_filter(
    names: List[str],
    dataset_records: List[dict],
    dataset_path: Path,
    gender: str | None,
) -> List[str]:
    if not names:
        return names
    if not prompt_yes_no("Do you want to review names one-by-one before starting the duel game?", default=False):
        return names
    print(f"Loaded {len(names)} names for guided filtering.")
    filtered = guided_filter_names(names)
    print(f"Guided filtering kept {len(filtered)} of {len(names)} names.")
    if len(filtered) < 2:
        raise ValueError("Need at least two names to continue after filtering.")
    maybe_save_filtered(filtered, dataset_records, dataset_path, gender)
    return filtered


def maybe_save_filtered(
    filtered_names: List[str],
    dataset_records: List[dict],
    dataset_path: Path,
    gender: str | None,
) -> None:
    if not filtered_names:
        return
    if not prompt_yes_no("Save this filtered list for future sessions?", default=False):
        return
    default_path = dataset_path.with_name(f"{dataset_path.stem}_filtered.json")
    raw_path = input(f"Output file path [{default_path}]: ").strip()
    target_path = Path(raw_path) if raw_path else default_path
    entries = select_records_for_names(dataset_records, filtered_names, gender)
    if not entries:
        print("No matching dataset entries found for the filtered names; nothing saved.")
        return
    save_filtered_records(entries, target_path)
    print(f"Saved {len(entries)} entries to {target_path}")


def capture_duel_snapshot(
    tracker: ScoreTracker, pair: Tuple[str, str], autosave_counter: int
) -> dict:
    return {
        "pair": pair,
        "autosave_counter": autosave_counter,
        "entries": {
            pair[0]: _entry_snapshot(tracker, pair[0]),
            pair[1]: _entry_snapshot(tracker, pair[1]),
        },
    }


def _entry_snapshot(tracker: ScoreTracker, name: str) -> dict | None:
    entry = tracker.entries.get(name)
    if entry is None:
        return None
    return {"wins": entry.wins, "losses": entry.losses, "rating": entry.rating}


def restore_duel_snapshot(tracker: ScoreTracker, snapshot: dict) -> int:
    for name, state in snapshot.get("entries", {}).items():
        if state is None:
            tracker.entries.pop(name, None)
            continue
        entry = tracker._get_entry(name)
        entry.wins = state["wins"]
        entry.losses = state["losses"]
        entry.rating = state["rating"]
    return int(snapshot.get("autosave_counter", 0))


def save_ranking_state(path: Path | None, tracker: ScoreTracker, names: Sequence[str]) -> None:
    if path is None:
        return
    state = tracker.to_state(names)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_ranking_state(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def maybe_resume_state(path: Path | None, mode: str) -> Tuple[ScoreTracker, List[str]] | None:
    payload = load_ranking_state(path)
    if not payload:
        return None
    saved_mode = payload.get("mode")
    saved_names = payload.get("names") or []
    if saved_mode != mode:
        print("Saved state uses a different scoring mode; ignoring it.")
        return None
    if not saved_names:
        print("Saved state is missing the name list; ignoring it.")
        return None
    if not prompt_yes_no(
        f"Found a saved {saved_mode} session with {len(saved_names)} names. Resume it?", default=True
    ):
        return None
    tracker, names = ScoreTracker.from_state(payload)
    print(f"Loaded ranking progress for {len(names)} names.")
    return tracker, names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pairwise ranking game for baby names.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DATA_PATH,
        help=f"Path to JSON dataset (default: {DATA_PATH})",
    )
    parser.add_argument(
        "--gender",
        choices=("female", "male"),
        default=None,
        help="Filter names by gender.",
    )
    parser.add_argument(
        "--mode",
        choices=("count", "elo"),
        default="count",
        help="Scoring mode. 'elo' keeps ratings, 'count' simply tallies wins.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible pair order.",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=None,
        help="Path to save/load ranking progress (default for game mode: data/ranking_state.json).",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Print an analysis of a persisted ranking state instead of starting the game.",
    )
    parser.add_argument(
        "--autosave-interval",
        type=int,
        default=0,
        help="Autosave ranking progress every N comparisons (0 disables).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    default_state_path = DATA_PATH.parent / "ranking_state.json"
    if args.analyze:
        if args.state is None:
            print("Analysis requires --state <path> to read a persisted ranking state.", file=sys.stderr)
            raise SystemExit(2)
        summary = summarize_state(load_state(args.state))
        print(format_analysis(summary))
        return

    state_path = args.state or default_state_path
    resume_payload = maybe_resume_state(state_path, args.mode)
    if resume_payload:
        tracker, names_for_game = resume_payload
    else:
        dataset_records = load_dataset_records(args.data)
        names = load_names(args.data, gender=args.gender)
        setup_seed = args.seed + 1 if args.seed is not None else None
        rng = random.Random(setup_seed)
        selected_names = perform_setup(names, mode=args.mode, rng=rng)
        filtered_names = maybe_guided_filter(selected_names, dataset_records, args.data, args.gender)
        tracker = ScoreTracker(mode=args.mode)
        names_for_game = filtered_names
    run_game(
        names_for_game,
        mode=args.mode,
        seed=args.seed,
        tracker=tracker,
        state_path=state_path,
        autosave_interval=max(0, args.autosave_interval),
    )


if __name__ == "__main__":
    main()
