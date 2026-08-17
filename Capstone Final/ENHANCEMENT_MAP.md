# Enhancement Map

This file keeps the three rubric categories distinct even though they are implemented in one final artifact.

## Software Design and Engineering
- Refactored one-cell notebook into modules with separate responsibilities.
- Added `AppConfig` and `.env` support instead of keeping deployment values in dashboard code.
- Added an application factory in `app.py`.
- Centralized logging configuration and improved exception boundaries.
- Moved validation into a reusable module.
- Added README, dependency list, docstrings, and automated tests.
- Added delete confirmation and selection-to-form behavior to improve safe user interaction.

## Algorithms and Data Structures
- Replaced binary rescue filtering with a weighted rescue suitability score.
- Stored rescue rules in a JSON-backed dictionary structure.
- Converted preferred breed/sex lists to sets for fast membership tests.
- Enriched each animal record with score, level, and explanation.
- Sorted candidates by score with deterministic tie breakers.
- Overall ranking complexity: O(n log n).

## Databases
- Retained safer CRUD layer from Milestone 4.
- Validates and normalizes data before writes.
- Uses single-record update/delete by default and refuses empty filters.
- Supports read projections, sorting, and limits.
- Creates indexes around common query fields.
- Writes modification history to an audit collection.
- Keeps MongoDB `_id` available to the dashboard as `record_id`.
