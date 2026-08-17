"""Application configuration for the CS-340 Animal Shelter dashboard.

Configuration is loaded from environment variables so deployment-specific
values and credentials do not have to be stored directly in source code.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

try:
    # python-dotenv makes local development easier by loading values from .env.
    from dotenv import load_dotenv
except ImportError:
    # The package is optional when environment variables are supplied externally.
    load_dotenv = None


@dataclass(frozen=True)
class AppConfig:
    """Immutable collection of settings needed to start the application."""

    # MongoDB connection settings.
    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str
    db_collection: str

    # Path to the JSON file used by the rescue-ranking enhancement.
    rescue_profiles_path: Path

    # Logging level can be changed without editing application code.
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "AppConfig":
        """Build and validate configuration from environment variables.

        If python-dotenv is installed, values from ``.env`` are loaded first.
        Existing operating-system environment variables take precedence.
        """
        # Load a local .env file when supported. override=False prevents the file
        # from replacing values already supplied by the operating environment.
        if load_dotenv is not None:
            load_dotenv(dotenv_path=env_file, override=False)

        # Collect the settings that must exist before a database connection can
        # be attempted. Keeping this check here lets the program fail early with
        # a useful message instead of failing later inside PyMongo.
        required = {
            "AAC_DB_USER": os.getenv("AAC_DB_USER"),
            "AAC_DB_PASSWORD": os.getenv("AAC_DB_PASSWORD"),
            "AAC_DB_HOST": os.getenv("AAC_DB_HOST"),
            "AAC_DB_PORT": os.getenv("AAC_DB_PORT"),
            "AAC_DB_NAME": os.getenv("AAC_DB_NAME"),
            "AAC_DB_COLLECTION": os.getenv("AAC_DB_COLLECTION"),
        }

        # Report all missing settings together so the user can correct them in
        # one pass rather than discovering them one at a time.
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing required database configuration: " + ", ".join(missing)
            )

        # MongoDB expects the port as an integer. Validate the conversion before
        # the value is stored in the configuration object.
        try:
            port = int(required["AAC_DB_PORT"])
        except (TypeError, ValueError) as exc:
            raise ValueError("AAC_DB_PORT must be an integer.") from exc

        # Allow the rescue-profile file to be overridden by an environment
        # variable while defaulting to rescue_profiles.json beside this module.
        profiles_path = Path(
            os.getenv(
                "AAC_RESCUE_PROFILES",
                str(Path(__file__).with_name("rescue_profiles.json")),
            )
        )

        # frozen=True on AppConfig prevents these settings from being changed
        # accidentally after the application has been configured.
        return cls(
            db_user=str(required["AAC_DB_USER"]),
            db_password=str(required["AAC_DB_PASSWORD"]),
            db_host=str(required["AAC_DB_HOST"]),
            db_port=port,
            db_name=str(required["AAC_DB_NAME"]),
            db_collection=str(required["AAC_DB_COLLECTION"]),
            rescue_profiles_path=profiles_path,
            log_level=os.getenv("AAC_LOG_LEVEL", "INFO").upper(),
        )
