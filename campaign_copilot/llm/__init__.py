"""Model access. `get_llm()` returns a mock or a real Claude client depending on MOCK_LLM."""

from campaign_copilot.llm.client import LLM, get_llm

__all__ = ["LLM", "get_llm"]
