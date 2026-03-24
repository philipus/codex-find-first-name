from __future__ import annotations

from name_finder.phonetics import analyze_word


def compare_syllables(name1: str, name2: str, language: str = "de") -> dict:
    """Compare two names using their normalized syllable sequences."""
    syllables1 = _extract_syllables(name1, language)
    syllables2 = _extract_syllables(name2, language)
    distance = _levenshtein_distance(syllables1, syllables2)
    max_len = max(len(syllables1), len(syllables2))

    return {
        "name1": name1,
        "name2": name2,
        "syllables1": syllables1,
        "syllables2": syllables2,
        "syllable_count_diff": abs(len(syllables1) - len(syllables2)),
        "first_syllable_match": _boundary_match(syllables1, syllables2, index=0),
        "last_syllable_match": _last_syllable_match(syllables1, syllables2),
        "levenshtein_distance": distance,
        "normalized_similarity_score": _normalized_similarity_score(distance, max_len),
    }


def _extract_syllables(name: str, language: str) -> list[str]:
    return list(analyze_word(name, language=language)["syllables"])


def _boundary_match(syllables1: list[str], syllables2: list[str], index: int) -> bool:
    if len(syllables1) <= index or len(syllables2) <= index:
        return False
    return syllables1[index] == syllables2[index]


def _last_syllable_match(syllables1: list[str], syllables2: list[str]) -> bool:
    if not syllables1 or not syllables2:
        return False
    return syllables1[-1] == syllables2[-1]


def _levenshtein_distance(sequence1: list[str], sequence2: list[str]) -> int:
    if not sequence1:
        return len(sequence2)
    if not sequence2:
        return len(sequence1)

    previous_row = list(range(len(sequence2) + 1))
    for row_index, left_value in enumerate(sequence1, start=1):
        current_row = [row_index]
        for column_index, right_value in enumerate(sequence2, start=1):
            substitution_cost = 0 if left_value == right_value else 1
            current_row.append(min(
                previous_row[column_index] + 1,
                current_row[column_index - 1] + 1,
                previous_row[column_index - 1] + substitution_cost,
            ))
        previous_row = current_row
    return previous_row[-1]


def _normalized_similarity_score(distance: int, max_len: int) -> float:
    if max_len == 0:
        return 1.0
    score = 1 - (distance / max_len)
    return max(0.0, min(1.0, score))
