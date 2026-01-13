
import pytest
from unittest.mock import MagicMock, patch
from src.graph.nodes import planner_node
from langchain_core.messages import HumanMessage
from src.graph.graph_types import State
from src.schemas.outputs import PlannerOutput, TaskStep

@pytest.mark.asyncio
async def test_ut03_planner_execution_plan():
    """UT-03: 複雑な要求に対し、論理的に整合性のある Execution Plan (JSON) を出力できるか検証 (Mock)"""
    
    # 状態設定
    initial_state: State = {
        "messages": [
            HumanMessage(content="AIによる教育変革についてのスライドを作って", name="user"),
            HumanMessage(content="承知しました。プランを作成します。", name="coordinator") # handoff後を想定
        ],
        "plan": [],
        "artifacts": {},
        "current_step_index": 0,
        "search_before_planning": False # 今回は検索ロジックはスキップ
    }
    
    # Mock LLM Response
    # 期待されるPlannerOutput
    expected_steps = [
        TaskStep(id=1, role="researcher", instruction="現在のAI教育市場のトレンドを調査する", description="市場調査"),
        TaskStep(id=2, role="storywriter", instruction="調査結果に基づき全5枚のスライド構成を作成する", description="構成作成"),
        TaskStep(id=3, role="visualizer", instruction="各スライドのビジュアルイメージを作成する", description="画像生成")
    ]
    expected_output = PlannerOutput(steps=expected_steps)
    
    mock_llm = MagicMock()
    structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = structured_llm
    structured_llm.invoke.return_value = expected_output
    
    with patch("src.graph.nodes.get_llm_by_type", return_value=mock_llm):
        # ノード実行
        result = planner_node(initial_state)
        
        # 検証
        assert result.goto == "supervisor", "Planner should route to Supervisor"
        
        # State更新の検証
        updated_plan = result.update["plan"]
        assert len(updated_plan) == 3
        assert updated_plan[0]["role"] == "researcher"
        assert updated_plan[1]["instruction"] == "調査結果に基づき全5枚のスライド構成を作成する"
        
        # ログメッセージ検証 (簡易)
        assert len(result.update["messages"]) > 0
        assert result.update["messages"][0].name == "planner"
