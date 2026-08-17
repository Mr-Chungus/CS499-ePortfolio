"""Unit tests for the reusable animal-record validation helpers."""

import unittest

from validation import normalize_animal_document, validate_animal_document


class ValidationTests(unittest.TestCase):
    """Verify valid input is accepted and common invalid input is rejected."""

    def test_valid_record(self):
        """A record with the required fields and a valid age should pass."""
        validate_animal_document(
            {
                "animal_type": "Dog",
                "breed": "Labrador",
                "age_upon_outcome_in_weeks": 52,
            }
        )

    def test_missing_required_field(self):
        """New records without a breed should be rejected."""
        with self.assertRaises(ValueError):
            validate_animal_document({"animal_type": "Dog"})

    def test_negative_age_rejected(self):
        """Negative ages should fail validation before reaching MongoDB."""
        with self.assertRaises(ValueError):
            validate_animal_document(
                {
                    "animal_type": "Dog",
                    "breed": "Lab",
                    "age_upon_outcome_in_weeks": -1,
                }
            )

    def test_invalid_latitude_rejected(self):
        """Latitude values outside -90 through 90 should be rejected."""
        with self.assertRaises(ValueError):
            validate_animal_document(
                {"animal_type": "Dog", "breed": "Lab", "location_lat": 120}
            )

    def test_partial_update_does_not_require_all_fields(self):
        """Updates may contain only the field being changed."""
        validate_animal_document({"name": "Max"}, partial=True)

    def test_numeric_strings_are_normalized(self):
        """Form-style numeric strings should be converted to numbers."""
        normalized = normalize_animal_document(
            {"age_upon_outcome_in_weeks": "52", "location_lat": "30.5"}
        )
        self.assertEqual(normalized["age_upon_outcome_in_weeks"], 52)
        self.assertEqual(normalized["location_lat"], 30.5)


if __name__ == "__main__":
    # Allow the test file to be executed directly in addition to test discovery.
    unittest.main()
