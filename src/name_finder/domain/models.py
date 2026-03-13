from dataclasses import dataclass
from enum import Enum


class NameGender(str, Enum):
    FEMALE = "female"
    MALE = "male"
    UNKNOWN = "unknown"


class NameCountry(str, Enum):
    GERMANY = "germany"
    UNKNOWN = "unknown"


class NameSource(str, Enum):
    POPULAR_FIRST_NAMES_DE = "popular-first-names-de"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FirstName:
    """Represents a first name candidate."""

    value: str
    source_url: str
    gender: NameGender = NameGender.UNKNOWN
    country: NameCountry = NameCountry.UNKNOWN
    source: NameSource = NameSource.UNKNOWN
