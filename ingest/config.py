"""Centralized configuration for the Ingest service (pydantic-settings)."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestSettings(BaseSettings):
    """Ingest settings from environment."""

    model_config = SettingsConfigDict(env_ignore_empty=True)

    vector_db_url: str = Field(
        "",
        validation_alias=AliasChoices("VECTOR_DB_URL", "CHROMA_URL"),
    )
