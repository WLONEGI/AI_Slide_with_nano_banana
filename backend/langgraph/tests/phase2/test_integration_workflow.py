
import pytest
from unittest.mock import MagicMock, patch
from src.graph.builder import build_graph
from langgraph.graph import START
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.graph_types import State
from src.schemas.outputs import PlannerOutput, TaskStep, ReviewOutput  # ReviewOutput needed for IT-03

@pytest.fixture
def mock_llm_factory():
    """Fixture to mock get_llm_by_type and return a controllable mock object."""
    with patch("src.graph.nodes.get_llm_by_type") as mock_factory:
        yield mock_factory

@pytest.mark.asyncio
async def test_it01_coordinator_to_planner(mock_llm_factory):
    """IT-01: Verify Coordinator hands off to Planner in the actual graph."""
    
    # Setup Mock LLM for Coordinator
    # Logic: "handoff_to_planner" keyword triggers goto="planner"
    mock_coord_llm = MagicMock()
    mock_coord_llm.invoke.return_value = AIMessage(content="Understood. handoff_to_planner")
    
    # Setup Mock LLM for Planner (to avoid error when Planner runs)
    # Planner needs to return a valid PlannerOutput structure
    mock_planner_llm = MagicMock()
    mock_planner_structured = MagicMock()
    mock_planner_structured.invoke.return_value = PlannerOutput(steps=[])
    mock_planner_llm.with_structured_output.return_value = mock_planner_structured
    
    # Configure Factory to return appropriate mock based on input
    def side_effect(llm_type):
        if llm_type == "basic": # Coordinator uses basic
            return mock_coord_llm
        if llm_type == "high_reasoning": # Planner uses high_reasoning
            return mock_planner_llm
        return MagicMock()
        
    mock_llm_factory.side_effect = side_effect
    
    # Build Graph
    graph = build_graph()
    
    # Input
    inputs = {"messages": [HumanMessage(content="Make slides about AI", name="user")]}
    
    # Execute Graph
    
    # Let's patch Supervisor to stop the graph.
    with patch("src.graph.nodes.supervisor_node") as mock_supervisor:
        from langgraph.types import Command
        mock_supervisor.return_value = Command(goto="__end__")
        
        # We also need to patch it in the builder module if it was imported there
        with patch("src.graph.builder.supervisor_node", mock_supervisor):
             graph = build_graph() # Rebuild with patched supervisor
             
             final_state = await graph.ainvoke(inputs)
             
             # Assertions
             # 1. Coordinator should have run (messages updated)
             # Coordinator handoff does NOT add a message to state (just returns goto).
             # So we check if PLANNER ran (which adds "Plan Generated").
             messages_content = [m.content for m in final_state["messages"]]
             assert any("Plan Generated" in c for c in messages_content)
             
             # 2. Supervisor should have been called (implying Planner finished and routed to it)
             # Planner returns Command(goto="supervisor") by default
             mock_supervisor.assert_called()


@pytest.mark.asyncio
async def test_it02_supervisor_delegation(mock_llm_factory):
    """IT-02: Supervisor delegates to the correct agent based on the plan."""
    
    # helper to dump
    step_data = TaskStep(id=1, role="researcher", instruction="Do work", description="test").model_dump()
    
    target_role = "researcher"
    
    with patch("src.graph.nodes.coordinator_node") as mock_coord:
        from langgraph.types import Command
        # Coordinator immediately sets up the plan and goes to Supervisor (skipping Planner)
        mock_coord.return_value = Command(
            goto="supervisor",
            update={
                "messages": [HumanMessage(content="Skip", name="user")],
                "plan": [step_data],
                "current_step_index": 0,
                "artifacts": {} # Ensure artifacts exists
            }
        )
        
        with patch("src.graph.nodes.research_agent") as mock_researcher_agent:
             # Make researcher just return done
             mock_researcher_agent.invoke.return_value = {"messages": [AIMessage(content="Done")]}
             
             # We also need Reviewer to stop the loop
             with patch("src.graph.nodes.reviewer_node") as mock_reviewer:
                 mock_reviewer.return_value = Command(goto="__end__") # Stop after reviewer
                 
                 # Rebuild graph
                 with patch("src.graph.builder.coordinator_node", mock_coord), \
                      patch("src.graph.builder.reviewer_node", mock_reviewer):
                     
                     graph = build_graph()
                     result = await graph.ainvoke({"messages": [], "artifacts": {}})
                     
                     # Verification
                     assert "step_1_research" in result["artifacts"]


@pytest.mark.asyncio
async def test_it03_reviewer_loop(mock_llm_factory):
    """IT-03: Reviewer reject triggers retry loop (Coordinator -> ... -> Reviewer -> Worker)."""
    
    target_role = "storywriter"
    step_data = TaskStep(id=1, role=target_role, instruction="Write", description="d").model_dump()
    
    with patch("src.graph.nodes.coordinator_node") as mock_coord:
        from langgraph.types import Command
        # 1. Setup state: Step 1 is Storywriter.
        mock_coord.return_value = Command(
            goto="reviewer",
            update={
                "plan": [step_data],
                "current_step_index": 0,
                "retry_count": 0,
                # Essential: Reviewer needs an artifact to review!
                "artifacts": {"step_1_story": "initial_content_v0"}
            }
        )
        
        # 2. Mock Storywriter
        with patch("src.graph.nodes.storywriter_node") as mock_storywriter:
            storywriter_call_count = 0
            def sw_side_effect(state):
                nonlocal storywriter_call_count
                storywriter_call_count += 1
                return Command(
                    goto="reviewer",
                    update={"artifacts": {f"step_1_story": "content"}}
                )
            mock_storywriter.side_effect = sw_side_effect

            # 3. Mock Reviewer LLM
            mock_review_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.invoke.side_effect = [
                ReviewOutput(approved=False, score=0.0, feedback="Bad"), # 1st check
                ReviewOutput(approved=True, score=1.0, feedback="Good")  # 2nd check
            ]
            mock_review_llm.with_structured_output.return_value = mock_structured
            
            # Setup factory for "reasoning" (which Reviewer uses)
            mock_llm_factory.side_effect = lambda t: mock_review_llm if t == "reasoning" else MagicMock()
            
            # Rebuild graph with patched nodes
            # Must also patch Supervisor to Stop the graph after the loop succeeds
            with patch("src.graph.builder.coordinator_node", mock_coord), \
                 patch("src.graph.builder.storywriter_node", mock_storywriter), \
                 patch("src.graph.builder.supervisor_node", return_value=Command(goto="__end__")):
                
                graph = build_graph()
                result = await graph.ainvoke({"messages": [], "artifacts": {}})
                
                # Verification
                assert storywriter_call_count == 1 # Called once during loop
                assert result["retry_count"] == 1


@pytest.mark.asyncio
async def test_it04_full_workflow_happy_path(mock_llm_factory):
    """IT-04: Full workflow simulation (Coord -> Planner -> Sup -> Res -> Rev -> Sup -> End)."""
    
    # We patch the NODES themselves to simulate the flow without needing complex LLM mocks.
    # This verifies the GRAPH TOPOLOGY and SUPERVISOR LOGIC.
    
    # Define a single-step plan
    plan_step = TaskStep(id=1, role="researcher", instruction="Search", description="desc")
    
    # 1. Patch Coordinator: Handoff to Planner
    with patch("src.graph.builder.coordinator_node") as mock_coord:
        from langgraph.types import Command
        mock_coord.return_value = Command(goto="planner")
        
        # 2. Patch Planner: Create Plan -> Supervisor
        with patch("src.graph.builder.planner_node") as mock_planner:
            mock_planner.return_value = Command(
                goto="supervisor",
                update={
                    "plan": [plan_step.model_dump()],
                    "current_step_index": 0,
                    "artifacts": {}
                }
            )
            
            # 3. Use REAL Supervisor Node to test the routing logic!
            
            # 4. Patch Researcher: Do work -> Reviewer
            with patch("src.graph.builder.research_node") as mock_researcher:
                mock_researcher.return_value = Command(
                    goto="reviewer",
                    update={"artifacts": {"step_1_research": "Done"}}
                )
                
                # 5. Patch Reviewer: Approve -> Supervisor
                # Strict requirement: Supervisor checks if last message name is 'reviewer'.
                with patch("src.graph.builder.reviewer_node") as mock_reviewer:
                    mock_reviewer.return_value = Command(
                        goto="supervisor",
                        update={
                            "messages": [AIMessage(content="Approved", name="reviewer")],
                            "feedback_history": {"1": ["OK"]}
                        }
                    )
                    
                    # Build Graph with these patches
                    graph = build_graph()
                    
                    # Execute
                    inputs = {"messages": [HumanMessage(content="Start", name="user")]}
                    final_state = await graph.ainvoke(inputs)
                    
                    # Verification
                    assert len(final_state["plan"]) == 1
                    assert final_state["artifacts"]["step_1_research"] == "Done"
                    assert final_state["messages"][-1].name == "reviewer" or \
                           (final_state["messages"][-1].name == "supervisor" and "completed" in final_state["messages"][-1].content)
                           
                    assert final_state["current_step_index"] == 1
                    mock_coord.assert_called()
                    mock_planner.assert_called()
                    mock_researcher.assert_called()
                    mock_reviewer.assert_called()
