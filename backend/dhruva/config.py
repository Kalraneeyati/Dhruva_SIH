"""Settings. Everything comes from the environment; no credential has a default."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "dhruva"
    env: str = "dev"

    database_url: str = "postgresql://dhruva:dhruva@postgres:5432/dhruva"
    redis_url: str = "redis://redis:6379/0"

    # Set once the pinned bundle exists; INCOIS omits an intermediate cert.
    # See CLAUDE.md. Never disable verification instead.
    earthdata_token: str | None = None
    incois_ca_bundle: str | None = None
    incois_erddap_base: str = "https://erddap.incois.gov.in/erddap"
    open_meteo_marine_base: str = "https://marine-api.open-meteo.com/v1"


settings = Settings()
