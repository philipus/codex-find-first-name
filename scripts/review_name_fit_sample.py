#!/usr/bin/env python3
"""Interactive reviewer for heuristic first-name/surname fit scores."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from name_finder.name_fit import score_name_fit


@dataclass(frozen=True)
class ConfusionMatrix:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int


@dataclass(frozen=True)
class ReviewSummary:
    sampled_first_names: int
    surnames: int
    generated_pairs: int
    reviewed_pairs: int
    good: int
    bad: int
    threshold: float
    confusion_matrix: ConfusionMatrix
    accuracy: float
    precision: float
    recall: float
    f1: float
    specificity: float
    balanced_accuracy: float
    quit_early: bool


def load_values_from_json(path: Path, *, key_candidates: Sequence[str]) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be a list of strings or objects")

    values: list[str] = []
    for item in payload:
        if isinstance(item, str):
            values.append(item)
            continue
        if isinstance(item, dict):
            value = _extract_first_string(item, key_candidates)
            if value is None:
                raise ValueError(
                    "JSON object entries must include one of keys: "
                    + ", ".join(key_candidates)
                )
            values.append(value)
            continue
        raise ValueError("Unsupported entry in JSON: expected string or object")

    cleaned = [value.strip() for value in values if value and value.strip()]
    if not cleaned:
        raise ValueError(f"No usable values found in {path}")
    return cleaned


def _extract_first_string(payload: dict, keys: Sequence[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def parse_surnames_csv(raw: str) -> list[str]:
    parsed = [part.strip() for part in raw.split(",") if part.strip()]
    if not parsed:
        raise ValueError("At least one surname must be provided")
    return parsed


def sample_first_names(names: Sequence[str], count: int, seed: int | None = None) -> list[str]:
    if count <= 0:
        return []
    sample_count = min(count, len(names))
    rng = random.Random(seed)
    if sample_count == len(names):
        sampled = list(names)
        rng.shuffle(sampled)
        return sampled
    return rng.sample(list(names), sample_count)


def build_name_pairs(
    first_names: Sequence[str],
    surnames: Sequence[str],
    *,
    seed: int | None = None,
    max_pairs: int | None = None,
) -> list[tuple[str, str]]:
    pairs = [(first_name, surname) for first_name in first_names for surname in surnames]
    rng = random.Random(seed)
    rng.shuffle(pairs)
    if max_pairs is not None and max_pairs >= 0:
        return pairs[:max_pairs]
    return pairs


def predicted_label_from_score(score_likelihood: float, threshold: float) -> int:
    return 1 if score_likelihood >= threshold else 0


def create_review_record(
    first_name: str,
    surname: str,
    score_payload: dict,
    threshold: float,
    human_label: int,
    session_id: str,
    language: str,
) -> dict:
    score_likelihood = float(score_payload["overall_score"])
    predicted_label = predicted_label_from_score(score_likelihood, threshold)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "first_name": first_name,
        "surname": surname,
        "language": language,
        "overall_score": score_likelihood,
        "overall_score_percent": score_payload["overall_score_percent"],
        "component_scores": score_payload["component_scores"],
        "feature_values": score_payload["feature_values"],
        "explanations": score_payload["explanations"],
        "threshold": threshold,
        "score_likelihood": score_likelihood,
        "predicted_label": predicted_label,
        "human_label": human_label,
        "is_correct": predicted_label == human_label,
    }


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def summarize_reviews(
    *,
    sampled_first_names: int,
    surnames: int,
    generated_pairs: int,
    reviewed_records: Sequence[dict],
    threshold: float,
    quit_early: bool,
) -> ReviewSummary:
    good = sum(1 for record in reviewed_records if record["human_label"] == 1)
    bad = sum(1 for record in reviewed_records if record["human_label"] == 0)
    matrix = _build_confusion_matrix(reviewed_records)

    precision = _safe_divide(matrix.true_positive, matrix.true_positive + matrix.false_positive)
    recall = _safe_divide(matrix.true_positive, matrix.true_positive + matrix.false_negative)
    specificity = _safe_divide(matrix.true_negative, matrix.true_negative + matrix.false_positive)
    accuracy = _safe_divide(
        matrix.true_positive + matrix.true_negative,
        len(reviewed_records),
    )
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    balanced_accuracy = (recall + specificity) / 2 if reviewed_records else 0.0

    return ReviewSummary(
        sampled_first_names=sampled_first_names,
        surnames=surnames,
        generated_pairs=generated_pairs,
        reviewed_pairs=len(reviewed_records),
        good=good,
        bad=bad,
        threshold=threshold,
        confusion_matrix=matrix,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        specificity=specificity,
        balanced_accuracy=balanced_accuracy,
        quit_early=quit_early,
    )


def _build_confusion_matrix(reviewed_records: Sequence[dict]) -> ConfusionMatrix:
    tp = fp = tn = fn = 0
    for record in reviewed_records:
        predicted = int(record["predicted_label"])
        human = int(record["human_label"])
        if predicted == 1 and human == 1:
            tp += 1
        elif predicted == 1 and human == 0:
            fp += 1
        elif predicted == 0 and human == 0:
            tn += 1
        else:
            fn += 1
    return ConfusionMatrix(true_positive=tp, false_positive=fp, true_negative=tn, false_negative=fn)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def review_pairs(
    pairs: Sequence[tuple[str, str]],
    *,
    output_jsonl: Path,
    threshold: float,
    session_id: str,
    language: str,
) -> tuple[list[dict], bool]:
    reviewed: list[dict] = []
    quit_early = False

    for index, (first_name, surname) in enumerate(pairs, start=1):
        score_payload = score_name_fit(first_name, surname, language=language)
        print("\n---")
        print(f"Pair {index}/{len(pairs)}: {first_name} + {surname}")
        print(f"Overall score: {score_payload['overall_score']:.4f} ({score_payload['overall_score_percent']:.2f}%)")
        print(f"Predicted label @ threshold {threshold:.2f}: "
              f"{predicted_label_from_score(score_payload['overall_score'], threshold)}")
        print("Explanations:")
        for explanation in score_payload["explanations"]:
            print(f"- {explanation}")

        while True:
            choice = input("Label? [1=good, 0=bad, q=quit]: ").strip().lower()
            if choice in {"1", "0", "q"}:
                break
            print("Please enter 1, 0, or q.")

        if choice == "q":
            quit_early = True
            break

        record = create_review_record(
            first_name,
            surname,
            score_payload,
            threshold,
            human_label=int(choice),
            session_id=session_id,
            language=language,
        )
        append_jsonl(output_jsonl, record)
        reviewed.append(record)

    return reviewed, quit_early


def summary_to_dict(summary: ReviewSummary) -> dict:
    return {
        "sampled_first_names": summary.sampled_first_names,
        "surnames": summary.surnames,
        "generated_pairs": summary.generated_pairs,
        "reviewed_pairs": summary.reviewed_pairs,
        "good": summary.good,
        "bad": summary.bad,
        "threshold": summary.threshold,
        "confusion_matrix": {
            "true_positive": summary.confusion_matrix.true_positive,
            "false_positive": summary.confusion_matrix.false_positive,
            "true_negative": summary.confusion_matrix.true_negative,
            "false_negative": summary.confusion_matrix.false_negative,
        },
        "accuracy": summary.accuracy,
        "precision": summary.precision,
        "recall": summary.recall,
        "f1": summary.f1,
        "specificity": summary.specificity,
        "balanced_accuracy": summary.balanced_accuracy,
        "quit_early": summary.quit_early,
    }


def format_summary(summary: ReviewSummary) -> str:
    matrix = summary.confusion_matrix
    lines = [
        "Review summary",
        f"- Sampled first names: {summary.sampled_first_names}",
        f"- Surnames: {summary.surnames}",
        f"- Generated pairs: {summary.generated_pairs}",
        f"- Reviewed pairs: {summary.reviewed_pairs}",
        f"- Good labels: {summary.good}",
        f"- Bad labels: {summary.bad}",
        f"- Threshold: {summary.threshold:.2f}",
        (
            "- Confusion matrix: "
            f"TP={matrix.true_positive}, FP={matrix.false_positive}, "
            f"TN={matrix.true_negative}, FN={matrix.false_negative}"
        ),
        f"- Accuracy: {summary.accuracy:.3f}",
        f"- Precision: {summary.precision:.3f}",
        f"- Recall: {summary.recall:.3f}",
        f"- F1: {summary.f1:.3f}",
        f"- Specificity: {summary.specificity:.3f}",
        f"- Balanced accuracy: {summary.balanced_accuracy:.3f}",
        f"- Quit early: {'yes' if summary.quit_early else 'no'}",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Human-in-the-loop reviewer for score_name_fit")
    parser.add_argument("--first-names-data", type=Path, required=True, help="Path to first-name JSON")
    parser.add_argument("--first-name-count", type=int, required=True, help="How many first names to sample")
    parser.add_argument("--surname-file", type=Path, default=None, help="Path to surname JSON")
    parser.add_argument("--surnames", default=None, help="Comma-separated surname list")
    parser.add_argument("--language", default="de", help="Language code for score_name_fit")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    parser.add_argument("--max-pairs", type=int, default=None, help="Optional cap on generated pairs")
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold for predicted label")
    parser.add_argument("--output-jsonl", type=Path, required=True, help="Persisted per-review rows")
    parser.add_argument("--summary-json", type=Path, required=True, help="Path for aggregate summary JSON")
    parser.add_argument("--session-id", default=None, help="Optional custom session id")
    args = parser.parse_args()
    _validate_args(args)
    return args


def _validate_args(args: argparse.Namespace) -> None:
    if (args.surname_file is None) == (args.surnames is None):
        raise ValueError("Provide exactly one of --surname-file or --surnames")
    if not (0.0 <= args.threshold <= 1.0):
        raise ValueError("--threshold must be between 0.0 and 1.0")


def main() -> None:
    args = parse_args()
    session_id = args.session_id or datetime.now(timezone.utc).strftime("name-fit-%Y%m%dT%H%M%SZ")

    first_names = load_values_from_json(args.first_names_data, key_candidates=("name",))
    sampled_first_names = sample_first_names(first_names, args.first_name_count, seed=args.seed)

    if args.surname_file is not None:
        surnames = load_values_from_json(args.surname_file, key_candidates=("surname", "name"))
    else:
        surnames = parse_surnames_csv(args.surnames)

    pairs = build_name_pairs(
        sampled_first_names,
        surnames,
        seed=args.seed,
        max_pairs=args.max_pairs,
    )

    reviewed_records, quit_early = review_pairs(
        pairs,
        output_jsonl=args.output_jsonl,
        threshold=args.threshold,
        session_id=session_id,
        language=args.language,
    )

    summary = summarize_reviews(
        sampled_first_names=len(sampled_first_names),
        surnames=len(surnames),
        generated_pairs=len(pairs),
        reviewed_records=reviewed_records,
        threshold=args.threshold,
        quit_early=quit_early,
    )

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(
        json.dumps(summary_to_dict(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("\n" + format_summary(summary))


if __name__ == "__main__":
    main()
