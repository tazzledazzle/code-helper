"""Centralized configuration for the Crew API (pydantic-settings)."""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_validate_startup(v: object) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes")
    return False


class CrewApiSettings(BaseSettings):
    """Crew API settings from environment. Env names preserved for existing deployments."""

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
    )

    runner_url: str = Field(
        "http://runner:8080",
        validation_alias=AliasChoices("RUNNER_URL", "RUNNER_SERVICE_URL"),
    )
    vector_db_url: str = Field("", validation_alias="VECTOR_DB_URL")
    llm_url: str = Field(
        "",
        validation_alias=AliasChoices("LLM_URL", "OPENAI_BASE_URL"),
    )
    llm_health_path: str | None = Field(None, validation_alias="LLM_HEALTH_PATH")
    k8s_namespace: str = Field("code-helper", validation_alias="K8S_NAMESPACE")
    ingest_image: str = Field("code-helper-ingest", validation_alias="INGEST_IMAGE")
    validate_startup: bool = Field(
        False,
        validation_alias="CREW_API_VALIDATE_DEPS",
    )

    @field_validator("validate_startup", mode="before")
    @classmethod
    def _coerce_validate_startup(cls, v: object) -> bool:
        return _parse_validate_startup(v)
