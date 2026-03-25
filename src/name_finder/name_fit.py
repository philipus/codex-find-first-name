from __future__ import annotations

from name_finder.phonetics import analyze_word
from name_finder.syllable_similarity import compare_syllables


SYLLABLE_DIFF_CAP = 3


def score_name_fit(first_name: str, surname: str, language: str = "de") -> dict:
    """Return an interpretable normalized (0.0-1.0) compatibility score."""
    features = extract_name_fit_features(first_name, surname, language=language)
    component_scores = _build_component_scores(features)
    overall_score = _calculate_overall_score(component_scores)

    return {
        "first_name": first_name,
        "surname": surname,
        "language": language,
        "overall_score": overall_score,
        "overall_score_percent": round(overall_score * 100, 2),
        "feature_values": features,
        "component_scores": component_scores,
        "explanations": _build_explanations(features, component_scores),
    }


def extract_name_fit_features(first_name: str, surname: str, language: str = "de") -> dict:
    """Extract deterministic phonetic and syllable-similarity features."""
    first_profile = analyze_word(first_name, language=language)
    surname_profile = analyze_word(surname, language=language)
    comparison = compare_syllables(first_name, surname, language=language)

    return {
        "first_name_syllables": list(first_profile["syllables"]),
        "surname_syllables": list(surname_profile["syllables"]),
        "first_name_syllable_count": first_profile["syllable_count"],
        "surname_syllable_count": surname_profile["syllable_count"],
        "absolute_syllable_count_difference": comparison["syllable_count_diff"],
        "first_syllable_match": comparison["first_syllable_match"],
        "last_syllable_match": comparison["last_syllable_match"],
        "levenshtein_distance": comparison["levenshtein_distance"],
        "normalized_similarity_score": comparison["normalized_similarity_score"],
    }


def _build_component_scores(features: dict) -> dict:
    syllable_balance_raw = _syllable_balance_score(
        features["absolute_syllable_count_difference"],
        cap=SYLLABLE_DIFF_CAP,
    )

    components = {
        "syllable_balance": _component_score(
            raw=syllable_balance_raw,
            weight=0.25,
            description="Penalizes large first-name/surname syllable-count differences.",
        ),
        "first_syllable_alignment": _component_score(
            raw=_boolean_score(features["first_syllable_match"]),
            weight=0.15,
            description="Rewards matching first syllables.",
        ),
        "last_syllable_alignment": _component_score(
            raw=_boolean_score(features["last_syllable_match"]),
            weight=0.20,
            description="Rewards matching ending syllables.",
        ),
        "sequence_similarity": _component_score(
            raw=features["normalized_similarity_score"],
            weight=0.40,
            description=(
                "Rewards similar syllable sequences via normalized Levenshtein similarity "
                "from compare_syllables(...)."
            ),
        ),
    }
    return components


def _component_score(raw: float, weight: float, description: str) -> dict:
    contribution = round(raw * weight, 4)
    return {
        "raw_score": round(raw, 4),
        "weight": weight,
        "contribution": contribution,
        "contribution_percent": round(contribution * 100, 2),
        "description": description,
    }


def _calculate_overall_score(component_scores: dict) -> float:
    return round(sum(component["contribution"] for component in component_scores.values()), 4)


def _build_explanations(features: dict, component_scores: dict) -> list[str]:
    return [
        (
            "Syllable counts "
            f"{features['first_name_syllable_count']} vs {features['surname_syllable_count']} "
            f"(diff={features['absolute_syllable_count_difference']}) "
            f"=> {component_scores['syllable_balance']['contribution_percent']}%."
        ),
        (
            f"First syllable match={features['first_syllable_match']} "
            f"=> {component_scores['first_syllable_alignment']['contribution_percent']}%."
        ),
        (
            f"Last syllable match={features['last_syllable_match']} "
            f"=> {component_scores['last_syllable_alignment']['contribution_percent']}%."
        ),
        (
            "Syllable sequence feature compares full syllable lists using Levenshtein distance: "
            f"distance={features['levenshtein_distance']}, similarity={features['normalized_similarity_score']:.2f} "
            f"=> {component_scores['sequence_similarity']['contribution_percent']}%."
        ),
    ]


def _syllable_balance_score(diff: int, cap: int) -> float:
    if cap <= 0:
        return 0.0
    return max(0.0, 1 - (diff / cap))


def _boolean_score(value: bool) -> float:
    return 1.0 if value else 0.0
