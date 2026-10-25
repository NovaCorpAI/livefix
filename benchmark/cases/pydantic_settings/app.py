"""Breaks on Pydantic v2: BaseSettings moved to the pydantic-settings package."""

from pydantic import BaseSettings  # moved out of pydantic in v2


class Settings(BaseSettings):
    app_name: str = "livefix"
    retries: int = 3


def load_settings():
    return Settings()
