"""Validation and normalization helpers for animal records.

Keeping validation outside the database class allows the same rules to be
reused by create/update operations and tested independently.
"""

from typing import Any, Dict

# New records must include these fields. Updates may provide only changed fields.
REQUIRED_FIELDS = {"animal_type", "breed"}

# These values are stored as numbers even if they arrive from a form as strings.
NUMERIC_FIELDS = {"age_upon_outcome_in_weeks", "location_lat", "location_long"}


def validate_animal_document(data: Dict[str, Any], partial: bool = False) -> None:
    """Validate an animal record before it is stored in MongoDB.

    ``partial=True`` is used for updates, where only the changed fields need to
    be supplied. A ValueError is raised when validation fails so the caller can
    return a meaningful message to the user instead of writing invalid data.
    """
    # CRUD operations expect a dictionary containing at least one field.
    if not isinstance(data, dict) or not data:
        raise ValueError("Data must be a non-empty dictionary.")

    # Creates require the minimum identifying fields; partial updates do not.
    if not partial:
        missing = sorted(field for field in REQUIRED_FIELDS if not data.get(field))
        if missing:
            raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    # Verify that numeric fields can actually be converted before any later
    # range checks or database writes are attempted.
    for field in NUMERIC_FIELDS:
        if field in data and data[field] not in (None, ""):
            try:
                float(data[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field} must be numeric.") from exc

    # An animal's age cannot logically be negative.
    age = data.get("age_upon_outcome_in_weeks")
    if age not in (None, "") and float(age) < 0:
        raise ValueError("age_upon_outcome_in_weeks cannot be negative.")

    # Latitude and longitude must fall within the valid geographic ranges used
    # by the map component.
    lat = data.get("location_lat")
    lon = data.get("location_long")
    if lat not in (None, "") and not -90 <= float(lat) <= 90:
        raise ValueError("location_lat must be between -90 and 90.")
    if lon not in (None, "") and not -180 <= float(lon) <= 180:
        raise ValueError("location_long must be between -180 and 180.")


def normalize_animal_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with known numeric values converted to Python numbers."""
    # Work on a copy so the caller's original dictionary is not modified.
    normalized = dict(data)

    # Dash form inputs may provide numeric values as strings. Converting them in
    # one place keeps the database representation consistent.
    for field in NUMERIC_FIELDS:
        value = normalized.get(field)
        if value in (None, ""):
            continue

        numeric = float(value)
        # Store whole-number values as ints and decimal values as floats.
        normalized[field] = int(numeric) if numeric.is_integer() else numeric

    return normalized
