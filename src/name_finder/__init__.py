"""name_finder application package."""

__all__ = ["compare_syllables", "score_name_fit"]

from name_finder.name_fit import score_name_fit
from name_finder.syllable_similarity import compare_syllables
