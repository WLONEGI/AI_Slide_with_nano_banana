
import pytest
from unittest.mock import MagicMock, patch
from src.graph.nodes import research_node
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.graph_types import State

@pytest.mark.asyncio
async def test_ut04_researcher_grounding():
    """UT-04: Researcherが正しくエージェントを呼び出し、結果を保存するか検証 (Mock)"""
    
    # Planのある状態を用意
    state: State = {
        "messages": [],
        "plan": [
            {"id": 1, "role": "researcher", "instruction": "AI市場規模を調査", "description": "調査"}
        ],
        "artifacts": {},
        "current_step_index": 0
    }
    
    # Mock Research Agent Response
    mock_agent_result = {
        "messages": [
            HumanMessage(content="Instruction...", name="supervisor"),
            AIMessage(content="調査結果報告:\n2025年のAI市場規模は約100兆円に達すると予測されています(出典: Gartner)。", name="researcher")
        ]
    }
    
    # src.graph.nodes.research_agent を patch
    with patch("src.graph.nodes.research_agent.invoke", return_value=mock_agent_result):
        # ノード実行
        result = research_node(state)
        
        # 検証
        assert result.goto == "reviewer", "Researcher should route to Reviewer"
        
        # Artifact保存の検証
        # キーは step_{id}_research
        assert "step_1_research" in result.update["artifacts"]
        saved_content = result.update["artifacts"]["step_1_research"]
        assert "100兆円" in saved_content
