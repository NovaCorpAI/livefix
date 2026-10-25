"""Stub the external SDKs so the pure-logic tests run without keys or installs."""

import sys
import types

if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _OpenAI:  # noqa: D401 - test stub
        def __init__(self, *a, **k):
            pass

    openai_stub.OpenAI = _OpenAI
    sys.modules["openai"] = openai_stub

if "tavily" not in sys.modules:
    tavily_stub = types.ModuleType("tavily")

    class _TavilyClient:  # noqa: D401 - test stub
        def __init__(self, *a, **k):
            pass

        def search(self, *a, **k):
            return {"results": []}

    tavily_stub.TavilyClient = _TavilyClient
    sys.modules["tavily"] = tavily_stub
