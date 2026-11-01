"""App settings. Every value can be overridden with an environment variable or the backend/.env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configurable values for the app, loaded from env vars or .env."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (SQLite file by default)
    DATABASE_URL: str = "sqlite:///./campusbite.db"

    # JWT
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Leave empty to use OpenAI. Set it to use any OpenAI-compatible provider, e.g. Google Gemini:
    # https://generativelanguage.googleapis.com/v1beta/openai/
    OPENAI_BASE_URL: str = ""
    AI_REQUESTS_PER_MINUTE: int = 5
    # Total AI questions allowed per day across all users (0 = no limit). Resets at midnight UTC.
    AI_DAILY_LIMIT: int = 100

    # Frontend address allowed to call the API (comma separated)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Background reminder job
    REMINDER_THRESHOLD_MINUTES: int = 15
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60

    # Create demo users, restaurants and dishes on first start
    SEED_DEMO_DATA: bool = True

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS split into a clean list for the CORS middleware."""
        origins = []
        for origin in self.CORS_ORIGINS.split(","):
            origin = origin.strip()
            # Skip empty entries, e.g. from a trailing comma
            if origin:
                origins.append(origin)
        return origins


# Single shared settings instance imported across the app
settings = Settings()
