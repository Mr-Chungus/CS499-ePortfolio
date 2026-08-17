"""Application factory and standalone entry point.

This module is intentionally small. Its job is to assemble the application's
separate components (configuration, database, rescue profiles, layout, and
callbacks) and return a ready-to-run Dash application.
"""

import logging
from typing import Any, Optional, Type

from dash import Dash

# Import each major application component from its own module. Keeping these
# responsibilities separate makes the project easier to test and maintain.
from animal_crud import AnimalShelter
from config import AppConfig
from dashboard_callbacks import register_callbacks
from dashboard_layout import build_layout
from rescue_ranking import load_profiles


def configure_logging(level: str) -> None:
    """Configure application-wide logging using the requested severity level."""
    # getattr converts strings such as "DEBUG" or "INFO" into logging constants.
    # If an invalid level is supplied, INFO is used as a safe default.
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_app(
    app_class: Type[Any] = Dash,
    config: Optional[AppConfig] = None,
) -> Any:
    """Build the dashboard and all of its dependencies in one central place."""
    # Load configuration from the environment unless a configuration object was
    # supplied explicitly, which is useful for testing or alternate deployments.
    config = config or AppConfig.from_env()
    configure_logging(config.log_level)

    # Create the MongoDB data-access layer and load the configurable rescue rules.
    db = AnimalShelter.from_config(config)
    profiles = load_profiles(config.rescue_profiles_path)

    # Construct the Dash/JupyterDash application, then attach its layout and
    # callback behavior. app_class allows the same factory to support either.
    app = app_class(__name__)
    app.layout = build_layout(profiles.keys())
    register_callbacks(app, db, profiles)

    # Keep shared dependencies attached to the app so they stay alive for the
    # application's lifetime and remain available for controlled shutdown/tests.
    app.animal_db = db
    app.rescue_profiles = profiles
    return app


if __name__ == "__main__":
    # Running this file directly starts the standalone Dash application.
    application = create_app()
    application.run(debug=True)
