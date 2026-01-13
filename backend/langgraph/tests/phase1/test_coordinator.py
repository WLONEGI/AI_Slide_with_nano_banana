
import pytest
from unittest.mock import MagicMock, patch
from src.graph.nodes import coordinator_node
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.graph_types import State

@pytest.mark.asyncio
async def test_ut01_coordinator_chat():
    """UT-01: 曖昧な指示や雑談に対し、handoffせずに対話を続けるか検証 (Mock)"""
    # ユーザー入力
    state: State = {
        "messages": [HumanMessage(content="こんにちは。元気？", name="user")],
        "plan": [],
        "artifacts": {},
        "current_step_index": 0
    }
    
    # Mock LLM Response
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="はい、元気です。どのようなご用件でしょうか？")
    
    with patch("src.graph.nodes.get_llm_by_type", return_value=mock_llm):
        # ノード実行
        result = coordinator_node(state)
        
        # 検証
        assert result.goto == "__end__"
        coordinator_response = result.update["messages"][0].content
        print(f"\n[UT-01 Output]: {coordinator_response}")
        assert "handoff_to_planner" not in coordinator_response
        assert str(coordinator_response) == "はい、元気です。どのようなご用件でしょうか？"


@pytest.mark.asyncio
async def test_ut02_coordinator_handoff():
    """UT-02: 明確な指示に対し、正しくPlannerへハンドオフするか検証 (Mock)"""
    # ユーザー入力
    user_input = "AIについてのスライドを10枚作って"
    
    state: State = {
        "messages": [HumanMessage(content=user_input, name="user")],
        "plan": [],
        "artifacts": {},
        "current_step_index": 0
    }
    
    # Mock LLM Response (Handoff keyword included)
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="要件を理解しました。Plannerに引き継ぎます。\nhandoff_to_planner")
    
    with patch("src.graph.nodes.get_llm_by_type", return_value=mock_llm):
        # ノード実行
        result = coordinator_node(state)
        
        # 検証
        assert result.goto == "planner", "Should handoff to planner when keyword is present"
