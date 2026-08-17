"""Configurable rescue-animal suitability scoring.

The original project used hard filters. This enhancement keeps the rescue
criteria configurable and ranks candidates according to how many preferred
criteria they meet. It does not require a database of every dog breed; breeds
not listed as preferred simply receive zero breed points.
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Set

# Type alias used to make function signatures easier to read. Each profile name
# maps to a dictionary containing breeds, sexes, age rules, and scoring weights.
ProfileMap = Dict[str, Dict[str, Any]]


def load_profiles(path: Path) -> ProfileMap:
    """Load and minimally validate rescue profiles from a JSON configuration."""
    # Read configuration separately from the Python source so rescue criteria
    # can be changed without rewriting the ranking algorithm itself.
    with Path(path).open("r", encoding="utf-8") as handle:
        profiles = json.load(handle)

    # The algorithm cannot operate if the JSON does not contain named profiles.
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("Rescue profile file must contain at least one profile.")

    # Every profile needs the same four sections for scoring to work reliably.
    required = {"preferred_breeds", "preferred_sexes", "age_weeks", "weights"}
    for name, profile in profiles.items():
        missing = required - set(profile)
        if missing:
            raise ValueError(
                f"Profile '{name}' is missing: {', '.join(sorted(missing))}"
            )

    return profiles


def _normalized_set(values: Iterable[Any]) -> Set[str]:
    """Normalize text and return a set for average O(1) membership tests."""
    # casefold() makes comparisons case-insensitive and more robust than lower().
    # A set is used because scoring frequently asks whether a value is preferred.
    return {str(value).strip().casefold() for value in values if value is not None}


def _has_valid_location(record: Mapping[str, Any]) -> bool:
    """Return True only when a record contains usable latitude/longitude data."""
    try:
        lat = float(record.get("location_lat"))
        lon = float(record.get("location_long"))
    except (TypeError, ValueError):
        # Missing or nonnumeric coordinates do not earn location points.
        return False

    # Use the standard geographic ranges also enforced by validation.py.
    return -90 <= lat <= 90 and -180 <= lon <= 180


def score_animal(
    record: Mapping[str, Any], profile: Mapping[str, Any]
) -> Dict[str, Any]:
    """Calculate a 0-100 suitability score and explain each matched criterion."""
    # Pull the configurable values out once so each comparison below is clear.
    weights = profile["weights"]
    preferred_breeds = _normalized_set(profile["preferred_breeds"])
    preferred_sexes = _normalized_set(profile["preferred_sexes"])
    age_rules = profile["age_weeks"]

    score = 0
    reasons: List[str] = []

    # Breed carries the highest weight because it is the strongest preferred
    # criterion in the current rescue profiles.
    breed = str(record.get("breed", "")).strip().casefold()
    if breed and breed in preferred_breeds:
        score += int(weights["breed"])
        reasons.append("preferred breed")

    # Age may arrive as text or a number, so convert safely before checking the
    # configured minimum and maximum range.
    age = record.get("age_upon_outcome_in_weeks")
    try:
        age_value = float(age)
    except (TypeError, ValueError):
        age_value = None

    if (
        age_value is not None
        and float(age_rules["minimum"]) <= age_value <= float(age_rules["maximum"])
    ):
        score += int(weights["age"])
        reasons.append("preferred age")

    # Preferred sex is checked with the same normalized set approach as breed.
    sex = str(record.get("sex_upon_outcome", "")).strip().casefold()
    if sex and sex in preferred_sexes:
        score += int(weights["sex"])
        reasons.append("preferred sex")

    # Valid coordinates earn the final location portion of the score.
    if _has_valid_location(record):
        score += int(weights["location"])
        reasons.append("location available")

    # Convert the numeric score into a simpler category for end users.
    if score >= 80:
        match_level = "Strong Match"
    elif score >= 50:
        match_level = "Possible Match"
    else:
        match_level = "Low Match"

    # Return both the score and an explanation so the ranking is transparent.
    return {
        "suitability_score": score,
        "match_level": match_level,
        "match_reasons": ", ".join(reasons)
        if reasons
        else "no preferred criteria matched",
    }


def rank_animals(
    records: Iterable[Mapping[str, Any]],
    profile_name: str,
    profiles: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Score and sort animals from strongest to weakest rescue candidate.

    Scoring each animal uses a fixed number of membership/range checks, so the
    scoring pass is O(n). Sorting n scored animals is O(n log n), which dominates
    the overall ranking operation.
    """
    # Reject invalid profile names rather than silently producing bad rankings.
    if profile_name not in profiles:
        raise ValueError(f"Unknown rescue profile: {profile_name}")

    ranked: List[Dict[str, Any]] = []
    profile = profiles[profile_name]

    # Copy each record before adding calculated fields so the original database
    # result is not modified by the ranking process.
    for record in records:
        enriched = dict(record)
        enriched.update(score_animal(record, profile))
        ranked.append(enriched)

    # Primary sort: highest suitability score first. Breed and name are used as
    # deterministic tie breakers so equal scores have a predictable order.
    ranked.sort(
        key=lambda item: (
            -int(item.get("suitability_score", 0)),
            str(item.get("breed", "")).casefold(),
            str(item.get("name", "")).casefold(),
        )
    )
    return ranked
