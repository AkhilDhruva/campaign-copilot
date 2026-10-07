import pytest

from campaign_copilot.agents.schemas import Plan
from campaign_copilot.llm import get_llm
from campaign_copilot.llm.client import LLMError, MockLLM


def test_default_is_mock(monkeypatch):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    assert isinstance(get_llm(), MockLLM)


def test_real_mode_without_key_fails_clearly(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        get_llm()


def test_mock_planner_is_deterministic_and_parses_goal():
    llm = MockLLM()
    goal = "Grow checking deposits 10% at our Dallas branches this quarter"
    a = llm.structured("planner", "sys", goal, Plan, {"goal": goal})
    b = llm.structured("planner", "sys", goal, Plan, {"goal": goal})
    assert a == b
    assert a.product == "checking"
    assert a.location == "Dallas"
    assert a.target_metric.startswith("+10%")
    assert len(a.steps) >= 3
    assert llm.calls[0]["agent"] == "planner" and llm.calls[0]["backend"] == "mock"


def test_mock_detects_other_products():
    llm = MockLLM()
    for goal, product in [
        ("Open 300 new high-yield savings accounts in Plano", "savings"),
        ("Drive credit card sign-ups among small businesses in Fort Worth", "credit_card"),
        ("Win 50 mortgage refinances in Frisco by March", "mortgage"),
    ]:
        assert llm.structured("planner", "", goal, Plan, {"goal": goal}).product == product


def test_unknown_agent_raises():
    with pytest.raises(LLMError):
        MockLLM().structured("nope", "", "", Plan, {})
