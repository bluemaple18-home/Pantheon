from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Mystic Engine"
    version: str = "0.1.0"
    default_timezone: str = os.getenv("MYSTIC_DEFAULT_TIMEZONE", "Asia/Taipei")
    database_url: str = os.getenv(
        "MYSTIC_DATABASE_URL",
        "sqlite:///app/database/ziwei_samples.sqlite",
    )
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None


settings = Settings()
