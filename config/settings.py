import os
from pathlib import Path

from bot.exceptions import ConfigurationError

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_env_file(_ENV_FILE)


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise ConfigurationError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in your credentials.",
            details={"missing_key": key, "env_file": str(_ENV_FILE)},
        )
    return value


class Settings:

    def __init__(self):
        self.api_key: str = _require("BINANCE_API_KEY")
        self.api_secret: str = _require("BINANCE_API_SECRET")
        self.base_url: str = os.getenv(
            "BINANCE_BASE_URL", "https://testnet.binancefuture.com"
        )
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    def __repr__(self) -> str:
        return (
            f"Settings(api_key=***{self.api_key[-4:]}, "
            f"base_url={self.base_url}, log_level={self.log_level})"
        )


settings = Settings()
