"""Centralized configuration for the Runner service (pydantic-settings)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunnerSettings(BaseSettings):
    """Runner settings from environment."""

    model_config = SettingsConfigDict(env_ignore_empty=True)

    allowed_root: str = Field("/tmp", validation_alias="ALLOWED_ROOT")
