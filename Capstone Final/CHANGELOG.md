# Change Log

## Starting point
`milestone_4_database_enhanced.zip` supplied by the student.

## Software Design and Engineering changes
- Split the original large notebook implementation into dedicated modules.
- Removed username/password literals from the dashboard code.
- Added environment-based configuration and `.env.example`.
- Added application factory and centralized dependency setup.
- Extracted validation into a reusable/testable module.
- Separated layout from controller callbacks.
- Added automated unit tests and project documentation.
- Added delete confirmation and automatic form population for a selected record.

## Algorithms and Data Structures changes
- Added `rescue_profiles.json` for configurable criteria and weights.
- Added `rescue_ranking.py` with weighted scoring and ranking.
- Uses sets for preferred breed and sex membership checks.
- Adds `suitability_score`, `match_level`, and `match_reasons` to ranked records.
- Ranks all dog candidates instead of requiring a complete data source for every dog breed.

## Database changes retained/integrated
- MongoDB connection ping, validation, structured results, safer single-record writes, optional bulk writes, indexes, audit logging, count helper, and explicit close method.
- Numeric values are now normalized before they are stored.
- Database configuration is passed from `AppConfig`, removing database settings from the CRUD module itself.
