# CS-499 Enhanced Animal Shelter Dashboard

This project is the enhanced version of the CS-340 Animal Shelter Dashboard used for the CS-499 capstone. One final artifact contains three distinct enhancement areas: Software Design and Engineering, Algorithms and Data Structures, and Databases.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and enter the MongoDB values for the environment where the AAC database is available.
3. Run the standalone application:
   ```bash
   python app.py
   ```
   Or open `ProjectTwoDashboard_all_enhancements.ipynb` in the SNHU/Jupyter environment.

## Enhancement 1: Software Design and Engineering

The original dashboard placed database setup, rescue-filter logic, layout, and callbacks in one notebook cell. The enhanced application separates responsibilities into modules:

- `config.py` - environment-based configuration
- `validation.py` - reusable validation/normalization
- `animal_crud.py` - MongoDB data-access layer
- `rescue_ranking.py` - rescue suitability algorithm
- `dashboard_layout.py` - view/layout
- `dashboard_callbacks.py` - controller/callback behavior
- `app.py` - dependency wiring/application factory

Other software-engineering improvements include structured logging, a single application factory, docstrings, clearer naming, reusable functions, a `.env.example`, a dependency list, and automated unit tests.

## Enhancement 2: Algorithms and Data Structures

The original application used hard MongoDB filters that either included or excluded an animal. The enhanced application uses a configurable rescue suitability algorithm.

When a rescue category is chosen, all dog records are evaluated using:

- preferred breed: 50 points
- preferred age range: 30 points
- preferred sex: 15 points
- valid location data: 5 points

The criteria and weights are stored in `rescue_profiles.json`, so rescue requirements can be changed without editing algorithm code. Preferred breeds and sexes are converted to Python sets for efficient membership checks. Each animal is enriched with a suitability score, match level, and matching reasons, then the list is sorted from strongest to weakest candidate. For n animals, scoring is linear and sorting makes the overall ranking O(n log n).

This design does **not** require data for every dog breed. A breed only receives breed points if it appears in the preferred-breed set for that rescue profile.

## Enhancement 3: Databases

The database enhancement from Milestone 4 is retained and integrated into the refactored application:

- environment-based database configuration
- fail-fast MongoDB connection ping
- input validation and numeric normalization
- consistent create/update/delete result objects
- projection, sorting, and limit support for reads
- `update_one()` / `delete_one()` by default
- explicit `many=True` for bulk operations
- rejected empty update/delete filters
- indexes for common query fields
- audit collection for create/update/delete activity
- preservation of MongoDB `_id` as dashboard-safe `record_id`
- Create / Update / Delete dashboard controls
- explicit delete confirmation

## Tests

The ranking algorithm and validation rules can be tested without a live MongoDB server:

```bash
python -m unittest discover -s tests -v
```
