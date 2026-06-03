"""Application configuration.

All configuration comes from environment variables (or a local `.env` file).
This is the "12-factor app" idea: the same code runs in dev, test, and prod,
and only the environment changes. Never hard-code secrets in source.

`pydantic-settings` reads the variables, validates their types, and gives us a
single typed `settings` object to import anywhere in the app.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # The variable names here match the keys in `.env.example`.
    # `DATABASE_URL` looks like: postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str

    # Secret used to sign JWT tokens. Anyone who knows it can forge tokens,
    # so in production this must be long, random, and stored in a secrets manager.
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Tells pydantic-settings to also read a `.env` file if present, and to match
    # env var names case-insensitively (DATABASE_URL -> database_url).
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


# Import this single instance elsewhere: `from app.config import settings`
settings = Settings()
