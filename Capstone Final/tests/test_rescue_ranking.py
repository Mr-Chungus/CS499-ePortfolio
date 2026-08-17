"""Unit tests for rescue suitability scoring and ranking behavior."""

import unittest
from pathlib import Path

from rescue_ranking import load_profiles, rank_animals, score_animal


class RescueRankingTests(unittest.TestCase):
    """Verify scoring, unknown values, ranking order, and profile validation."""

    @classmethod
    def setUpClass(cls):
        """Load the real project profiles once for all ranking tests."""
        cls.profiles = load_profiles(
            Path(__file__).resolve().parents[1] / "rescue_profiles.json"
        )

    def test_full_water_rescue_match_scores_100(self):
        """An animal matching every Water Rescue criterion should score 100."""
        animal = {
            "name": "Scout",
            "breed": "Labrador Retriever Mix",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 52,
            "location_lat": 30.2,
            "location_long": -97.7,
        }
        result = score_animal(animal, self.profiles["Water Rescue"])
        self.assertEqual(result["suitability_score"], 100)
        self.assertEqual(result["match_level"], "Strong Match")

    def test_unknown_breed_does_not_need_breed_profile(self):
        """A nonpreferred breed can still earn points from other criteria."""
        animal = {
            "breed": "Mixed Breed",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 52,
            "location_lat": 30.2,
            "location_long": -97.7,
        }
        result = score_animal(animal, self.profiles["Water Rescue"])
        self.assertEqual(result["suitability_score"], 50)
        self.assertEqual(result["match_level"], "Possible Match")

    def test_rank_animals_sorts_highest_score_first(self):
        """The strongest candidate should appear before a lower-scoring one."""
        animals = [
            {"name": "Low", "breed": "Mixed Breed"},
            {
                "name": "High",
                "breed": "Labrador Retriever Mix",
                "sex_upon_outcome": "Intact Female",
                "age_upon_outcome_in_weeks": 52,
                "location_lat": 30,
                "location_long": -97,
            },
        ]
        ranked = rank_animals(animals, "Water Rescue", self.profiles)
        self.assertEqual(ranked[0]["name"], "High")
        self.assertGreater(
            ranked[0]["suitability_score"], ranked[1]["suitability_score"]
        )

    def test_unknown_profile_rejected(self):
        """A profile name not found in the configuration should raise an error."""
        with self.assertRaises(ValueError):
            rank_animals([], "Not A Profile", self.profiles)


if __name__ == "__main__":
    # Allow the test file to be run directly in addition to test discovery.
    unittest.main()
