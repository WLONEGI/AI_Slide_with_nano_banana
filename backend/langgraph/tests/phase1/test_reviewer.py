
import pytest
from unittest.mock import MagicMock, patch
from src.graph.nodes import reviewer_node
from langchain_core.messages import HumanMessage
from src.graph.graph_types import State
from src.schemas.outputs import ReviewOutput

@pytest.mark.asyncio
async def test_ut06_reviewer_reject():
    """UT-06(a): 品質の低い成果物をリジェクトし、Workerに差し戻すか検証"""
    
    # State: Storywriterのステップ、成果物あり
    state: State = {
        "messages": [],
        "plan": [
            {"id": 2, "role": "storywriter", "instruction": "スライド作成", "description": "執筆"}
        ],
        "artifacts": {
            "step_2_story": "{\"slides\": []}" # 空っぽのスライド（不備）
        },
        "current_step_index": 0,
        "retry_count": 0,
        "feedback_history": {}
    }
    
    # Mock LLM (Critic) -> Reject
    mock_review = ReviewOutput(approved=False, score=0.3, feedback="スライドが含まれていません。指示に従ってください。")
    
    mock_llm = MagicMock()
    structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = structured_llm
    structured_llm.invoke.return_value = mock_review
    
    with patch("src.graph.nodes.get_llm_by_type", return_value=mock_llm):
        result = reviewer_node(state)
        
        # 検証
        # Rejectされたので、role="storywriter" に戻るはず
        assert result.goto == "storywriter"
        
        # updateの内容
        assert result.update["retry_count"] == 1
        assert "Review Feedback" in result.update["messages"][0].content
        assert "REJECTED" in result.update["feedback_history"]["2"][0]


@pytest.mark.asyncio
async def test_ut06_reviewer_max_retry():
    """UT-06(b): リトライ上限(Max Retries)に達した場合、Supervisorにエスカレーションするか検証"""
    
    state: State = {
        "messages": [],
        "plan": [
             {"id": 2, "role": "storywriter", "instruction": "スライド作成", "description": "執筆"}
        ],
        "artifacts": {
            "step_2_story": "still bad output"
        },
        "current_step_index": 0,
        "retry_count": 3, # 既に3回リトライ済み
        "feedback_history": {}
    }
    
    # Mock LLM (Critic) -> Reject
    mock_review = ReviewOutput(approved=False, score=0.1, feedback="依然として改善が見られません。")
    
    mock_llm = MagicMock()
    structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = structured_llm
    structured_llm.invoke.return_value = mock_review
    
    with patch("src.graph.nodes.get_llm_by_type", return_value=mock_llm):
        result = reviewer_node(state)
        
        # 検証
        # Max Retries なので Supervisor にエスカレーション
        assert result.goto == "supervisor"
        
        # エラーコンテキストがセットされているか
        assert "Failed criteria after 3 retries" in result.update["error_context"]
