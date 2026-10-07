"""One narrow interface to the model: `structured(agent, system, user, schema, context)`.

Two implementations:

* `MockLLM` (MOCK_LLM=1, the default): deterministic, offline, free. It ignores the prompt text
  and builds the schema object from `context`, which is the same structured data the prompt was
  rendered from. Outputs are stable across runs, so tests and evals are reproducible.
* `AnthropicLLM` (MOCK_LLM=0): calls Claude through the official SDK with structured outputs,
  so the response is guaranteed to validate against the pydantic schema.

Both record every call in `self.calls` so the audit log can show what the model was asked.
"""

from __future__ import annotations

import os
import time
from typing import Any, TypeVar

from pydantic import BaseModel

from campaign_copilot.llm import mock as mock_impl

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "claude-opus-5-5"


class LLMError(RuntimeError):
    """Raised when the model refuses or returns something unusable."""


class LLM:
    """Base class. Subclasses implement `_structured`."""

    name = "base"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def structured(
        self,
        agent: str,
        system: str,
        user: str,
        schema: type[T],
        context: dict[str, Any] | None = None,
    ) -> T:
        started = time.perf_counter()
        result = self._structured(agent, system, user, schema, context or {})
        self.calls.append(
            {
                "agent": agent,
                "backend": self.name,
                "schema": schema.__name__,
                "prompt_chars": len(system) + len(user),
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        )
        return result

    def _structured(
        self, agent: str, system: str, user: str, schema: type[T], context: dict[str, Any]
    ) -> T:
        raise NotImplementedError


class MockLLM(LLM):
    name = "mock"

    def _structured(
        self, agent: str, system: str, user: str, schema: type[T], context: dict[str, Any]
    ) -> T:
        builder = mock_impl.BUILDERS.get(agent)
        if builder is None:
            raise LLMError(f"MockLLM has no builder for agent {agent!r}")
        result = builder(context)
        if not isinstance(result, schema):
            raise LLMError(
                f"mock for {agent!r} returned {type(result).__name__}, not {schema.__name__}"
            )
        return result


class AnthropicLLM(LLM):
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        super().__init__()
        import anthropic  # imported here so mock mode never needs the SDK or a key

        self._anthropic = anthropic
        self.model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
        self.client = anthropic.Anthropic()

    def _structured(
        self, agent: str, system: str, user: str, schema: type[T], context: dict[str, Any]
    ) -> T:
        a = self._anthropic
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
                output_config={"effort": "medium"},
            )
        except a.RateLimitError as exc:
            raise LLMError(f"rate limited by the model API: {exc.message}") from exc
        except a.APIStatusError as exc:
            raise LLMError(f"model API error {exc.status_code}: {exc.message}") from exc
        except a.APIConnectionError as exc:
            raise LLMError("could not reach the model API") from exc

        if response.stop_reason == "refusal":
            detail = response.stop_details.explanation if response.stop_details else ""
            raise LLMError(f"model declined the {agent} request: {detail}")
        if response.parsed_output is None:
            raise LLMError(f"model returned no structured output for {agent}")
        return response.parsed_output


def mock_mode() -> bool:
    return os.environ.get("MOCK_LLM", "1").strip() not in ("0", "false", "False", "")


def get_llm() -> LLM:
    """Pick the backend from the environment. Mock unless MOCK_LLM=0."""
    if mock_mode():
        return MockLLM()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError(
            "MOCK_LLM=0 but ANTHROPIC_API_KEY is not set. Put it in .env or use MOCK_LLM=1."
        )
    return AnthropicLLM()
