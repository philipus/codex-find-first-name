#!/usr/bin/env python3
"""Interactive phonetics review helper."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from name_finder.phonetics import analyze_word


@dataclass
class ReviewStats:
    sampled: int
    reviewed: int
    good: int
    bad: int
    quit_early: bool
    bad_cases: list[dict]


def load_names_from_json(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of strings or objects with a 'name' field")
    names: list[str] = []
    for item in data:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and "name" in item and isinstance(item["name"], str):
            names.append(item["name"])
        else:
            raise ValueError("Unsupported entry in JSON: expected string or object with 'name'")
    if not names:
        raise ValueError("No names found in the input file")
    return names


def sample_names(names: Sequence[str], count: int, seed: int | None = None) -> list[str]:
    if count <= 0:
        return []
    sample_count = min(len(names), count)
    rng = random.Random(seed)
    pool = list(names)
    if sample_count == len(pool):
        rng.shuffle(pool)
        return pool
    return rng.sample(pool, sample_count)


def parse_corrected_syllables(raw: str) -> list[str]:
    cleaned = [part.strip() for part in raw.split(",") if part.strip()]
    if not cleaned:
        raise ValueError("At least one corrected syllable is required for a bad label")
    return cleaned


def create_review_record(
    name: str,
    language: str,
    analysis: dict,
    label: int,
    corrected_syllables: list[str] | None,
) -> dict:
    return {
        "name": name,
        "language": language,
        "normalized_word": analysis["normalized_word"],
        "predicted_syllables": analysis["syllables"],
        "predicted_syllable_count": analysis["syllable_count"],
        "label": label,
        "corrected_syllables": corrected_syllables,
    }


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_summary(
    sampled: int,
    reviewed_records: list[dict],
    quit_early: bool,
) -> ReviewStats:
    good = sum(1 for record in reviewed_records if record["label"] == 1)
    bad = sum(1 for record in reviewed_records if record["label"] == 0)
    bad_cases = [
        {
            "name": record["name"],
            "predicted": record["predicted_syllables"],
            "corrected": record["corrected_syllables"],
        }
        for record in reviewed_records
        if record["label"] == 0
    ]
    return ReviewStats(
        sampled=sampled,
        reviewed=len(reviewed_records),
        good=good,
        bad=bad,
        quit_early=quit_early,
        bad_cases=bad_cases,
    )


def format_summary(stats: ReviewStats) -> str:
    lines = [
        "Review summary",
        f"- Sampled: {stats.sampled}",
        f"- Reviewed: {stats.reviewed}",
        f"- Good: {stats.good}",
        f"- Bad: {stats.bad}",
        f"- Quit early: {'yes' if stats.quit_early else 'no'}",
    ]
    if stats.bad_cases:
        lines.append("\nBad cases:")
        for case in stats.bad_cases:
            lines.append(
                f"- {case['name']}: predicted {case['predicted']} -> corrected {case['corrected']}"
            )
    return "\n".join(lines)


def review_sample(names: Sequence[str], language: str, output_path: Path) -> ReviewStats:
    reviewed: list[dict] = []
    quit_early = False
    for name in names:
        analysis = analyze_word(name, language)
        print("\n---")
        print(f"Name: {name}")
        print(f"Normalized: {analysis['normalized_word']}")
        print(f"Predicted syllables: {analysis['syllables']}")
        print(f"Syllable count: {analysis['syllable_count']}")
        while True:
            choice = input("Label? [1=good, 0=bad, q=quit]: ").strip().lower()
            if choice not in {"1", "0", "q"}:
                print("Please enter 1, 0, or q.")
                continue
            break
        if choice == "q":
            quit_early = True
            break
        label = int(choice)
        corrected: list[str] | None = None
        if label == 0:
            while True:
                raw = input("Corrected syllables (comma-separated): ").strip()
                try:
                    corrected = parse_corrected_syllables(raw)
                    break
                except ValueError as error:
                    print(error)
        record = create_review_record(name, language, analysis, label, corrected)
        append_jsonl(output_path, record)
        reviewed.append(record)
    return build_summary(len(names), reviewed, quit_early)


def main() -> None:
    parser = argparse.ArgumentParser(description="Human-in-the-loop phonetics reviewer")
    parser.add_argument("--data", type=Path, required=True, help="Path to JSON names file")
    parser.add_argument("--language", default="de", help="Language code (default: de)")
    parser.add_argument("--count", type=int, required=True, help="Number of names to review")
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL path")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    args = parser.parse_args()

    names = load_names_from_json(args.data)
    sampled = sample_names(names, args.count, seed=args.seed)
    summary = review_sample(sampled, args.language, args.output)
    print("\n" + format_summary(summary))


if __name__ == "__main__":
    main()
