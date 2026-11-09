from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]  # repo root
API_DIR = ROOT / "apps" / "api"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # default = the local docker-compose database (documented in .env.example)
    database_url: str = "postgresql+psycopg://touchline:local_dev_password@localhost:5433/touchline"

    @field_validator("database_url", mode="before")
    @classmethod
    def _driver(cls, v):
        """Hosted Postgres (Render, Neon, Supabase) hands out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver."""
        if isinstance(v, str):
            for scheme in ("postgres://", "postgresql://"):
                if v.startswith(scheme):
                    return "postgresql+psycopg://" + v[len(scheme):]
        return v

    # Browser origins allowed to call the API (comma-separated). Set to the deployed web URL in production.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Optional regex for more origins, e.g. Vercel preview deploys: https://touchline-ai-.*\.vercel\.app
    cors_origin_regex: str = ""

    # Public-demo protection for the analyst (see app/core/limits.py).
    trust_proxy: bool = False  # true behind a reverse proxy that sets X-Forwarded-For (Render, Fly, ...)
    analyst_rate_per_minute: int = 6
    analyst_daily_per_client: int = 40
    analyst_daily_budget_usd: float = 10.0
    analyst_max_concurrent: int = 3

    # LLM for the analyst agent. The key may also come from OPENAI_API_KEY / ANTHROPIC_API_KEY.
    llm_provider: str = "openai"  # openai | anthropic
    llm_api_key: str | None = None
    llm_model: str = ""  # empty = the provider's default (openai: gpt-5.6-luna, anthropic: claude-opus-5-5)
    llm_effort: str = ""  # reasoning effort. Empty = provider default (openai: "none", anthropic: "medium")
    llm_max_steps: int = 8  # model turns per question before giving up
    llm_refusal_fallback: bool = True  # Anthropic only: server-side fallback if the model declines a request


settings = Settings()
