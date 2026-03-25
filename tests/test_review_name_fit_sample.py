from __future__ import annotations

import pytest

from scripts.review_name_fit_sample import (
    build_name_pairs,
    create_review_record,
    parse_surnames_csv,
    predicted_label_from_score,
    sample_first_names,
    summarize_reviews,
)


def test_parse_surnames_csv_requires_values() -> None:
    with pytest.raises(ValueError):
        parse_surnames_csv(" ,  ")


def test_parse_surnames_csv_splits_and_trims() -> None:
    result = parse_surnames_csv("floegel, schaefer ,mayer")

    assert result == ["floegel", "schaefer", "mayer"]


def test_sample_first_names_is_deterministic() -> None:
    names = ["Anna", "Berta", "Clara", "Dora", "Eva"]

    first = sample_first_names(names, 3, seed=7)
    second = sample_first_names(names, 3, seed=7)

    assert first == second


def test_build_name_pairs_applies_max_pairs() -> None:
    pairs = build_name_pairs(
        ["Anna", "Berta"],
        ["Mayer", "Schaefer"],
        seed=42,
        max_pairs=3,
    )

    assert len(pairs) == 3
    assert set(pairs).issubset({
        ("Anna", "Mayer"),
        ("Anna", "Schaefer"),
        ("Berta", "Mayer"),
        ("Berta", "Schaefer"),
    })


def test_predicted_label_from_score_uses_threshold() -> None:
    assert predicted_label_from_score(0.49, 0.5) == 0
    assert predicted_label_from_score(0.5, 0.5) == 1


def test_create_review_record_maps_payload_and_prediction() -> None:
    score_payload = {
        "overall_score": 0.6,
        "overall_score_percent": 60.0,
        "component_scores": {"sequence_similarity": {"contribution": 0.2}},
        "feature_values": {"normalized_similarity_score": 0.5},
        "explanations": ["example"],
    }

    record = create_review_record(
        "Anna",
        "Mayer",
        score_payload,
        threshold=0.5,
        human_label=1,
        session_id="session-1",
        language="de",
    )

    assert record["first_name"] == "Anna"
    assert record["surname"] == "Mayer"
    assert record["overall_score"] == pytest.approx(0.6)
    assert record["score_likelihood"] == pytest.approx(0.6)
    assert record["predicted_label"] == 1
    assert record["is_correct"] is True


def test_summarize_reviews_calculates_confusion_matrix_metrics() -> None:
    reviewed_records = [
        {"predicted_label": 1, "human_label": 1},  # tp
        {"predicted_label": 1, "human_label": 0},  # fp
        {"predicted_label": 0, "human_label": 0},  # tn
        {"predicted_label": 0, "human_label": 1},  # fn
    ]

    summary = summarize_reviews(
        sampled_first_names=2,
        surnames=2,
        generated_pairs=4,
        reviewed_records=reviewed_records,
        threshold=0.5,
        quit_early=False,
    )

    assert summary.confusion_matrix.true_positive == 1
    assert summary.confusion_matrix.false_positive == 1
    assert summary.confusion_matrix.true_negative == 1
    assert summary.confusion_matrix.false_negative == 1
    assert summary.accuracy == pytest.approx(0.5)
    assert summary.precision == pytest.approx(0.5)
    assert summary.recall == pytest.approx(0.5)
    assert summary.f1 == pytest.approx(0.5)
    assert summary.specificity == pytest.approx(0.5)
    assert summary.balanced_accuracy == pytest.approx(0.5)
