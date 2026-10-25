"""Thin wrapper over the OpenAI-compatible Nebius Token Factory chat endpoint."""

from __future__ import annotations

from openai import OpenAI

from .config import Config
from .tracing import traceable


class NebiusChat:
    def __init__(self, config: Config):
        self._model = config.nebius_model
        self._client = OpenAI(
            api_key=config.nebius_api_key,
            base_url=config.nebius_base_url,
        )

    @property
    def model(self) -> str:
        return self._model

    @traceable(run_type="llm", name="nemotron.complete")
    def complete(self, system: str, user: str, temperature: float = 0.1) -> str:
        """Return the assistant message text for a single-shot prompt."""
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
