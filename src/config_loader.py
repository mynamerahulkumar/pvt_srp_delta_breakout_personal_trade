import json
import os
from dotenv import load_dotenv


def load_config(config_path="config.json", env_path=".env"):
    """Load configuration from config.json and .env file."""
    load_dotenv(env_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Inject credentials from environment
    config["delta_api_key"] = os.environ.get("DELTA_API_KEY", "")
    config["delta_api_secret"] = os.environ.get("DELTA_API_SECRET", "")
    config["delta_base_url"] = os.environ.get(
        "DELTA_BASE_URL", "https://api.india.delta.exchange"
    )
    config["environment"] = os.environ.get("ENV", config.get("environment", "local"))

    # Validate required fields
    if not config["delta_api_key"]:
        raise ValueError("DELTA_API_KEY not set in .env")
    if not config["delta_api_secret"]:
        raise ValueError("DELTA_API_SECRET not set in .env")
    if not config.get("symbols"):
        raise ValueError("No symbols configured in config.json")

    return config
