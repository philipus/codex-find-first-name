#!/usr/bin/env python3
"""Simple CLI pairwise ranking game for baby names."""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

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


def pick_pair(names: List[str], rng: random.Random) -> Tuple[str, str]:
    first, second = rng.sample(names, 2)
    return first, second


def run_game(names: Iterable[str], mode: str, seed: int | None = None) -> None:
    rng = random.Random(seed)
    tracker = ScoreTracker(mode=mode)
    names_list = list(names)

    print("Pairwise Name Duel")
    print("-------------------")
    print("Choose your favorite between two names.")
    print("Controls: 1 = first, 2 = second, s = skip, q = quit.")
    print()

    while True:
        first, second = pick_pair(names_list, rng)
        print(f"1) {first}")
        print(f"2) {second}")
        choice = input("Your pick [1/2/s/q]: ").strip().lower()
        if choice == "q":
            break
        if choice == "s":
            print("Skipped.\n")
            continue
        if choice == "1":
            tracker.record(first, second)
            print(f"You preferred {first}.\n")
        elif choice == "2":
            tracker.record(second, first)
            print(f"You preferred {second}.\n")
        else:
            print("Invalid input, try again.\n")

    print("\nResults")
    print("-------")
    ranking = tracker.ranking()
    if not ranking:
        print("No results recorded. Play at least one round next time!")
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    names = load_names(args.data, gender=args.gender)
    setup_seed = args.seed + 1 if args.seed is not None else None
    rng = random.Random(setup_seed)
    selected_names = perform_setup(names, mode=args.mode, rng=rng)
    run_game(selected_names, mode=args.mode, seed=args.seed)


if __name__ == "__main__":
    main()
