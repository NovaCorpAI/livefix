"""Runtime configuration, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _getenv(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    if value is not None:
        value = value.strip()
    return value or default


@dataclass(frozen=True)
class Config:
    nebius_api_key: str
    nebius_base_url: str
    nebius_model: str
    tavily_api_key: str | None

    @classmethod
    def from_env(cls) -> "Config":
        api_key = _getenv("NEBIUS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "NEBIUS_API_KEY is not set. Copy .env.example to .env, fill it in, "
                "and load it (for example with `set -a; . ./.env; set +a`)."
            )
        return cls(
            nebius_api_key=api_key,
            nebius_base_url=_getenv(
                "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"
            ),
            nebius_model=_getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
            tavily_api_key=_getenv("TAVILY_API_KEY"),
        )
