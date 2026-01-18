import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.service.workflow_service import run_agent_workflow, _manager
from langchain_core.messages import AIMessage

@pytest.fixture
def mock_graph():
    """WorkflowManager のグラフをモックする"""
    _manager.initialized = True
    _manager.graph = MagicMock()
    yield _manager.graph
    _manager.initialized = False
    _manager.graph = None

@pytest.mark.asyncio
async def test_run_agent_workflow_basic_flow(mock_graph):
    # Mock astream_events to yield some events
    async def event_generator(*args, **kwargs):
        events = [
            {"event": "on_chain_start", "name": "planner", "data": {}, "metadata": {}},
            {"event": "on_chat_model_stream", "name": "coordinator", "data": {"chunk": AIMessage(content="Hello", id="1")}, "metadata": {"checkpoint_ns": "coordinator:1"}},
            {"event": "on_chat_model_stream", "name": "coordinator", "data": {"chunk": AIMessage(content=" World", id="2")}, "metadata": {"checkpoint_ns": "coordinator:1"}},
        ]
        for e in events:
            yield e

    mock_graph.astream_events = event_generator
    
    user_input = [{"role": "user", "content": "Hi"}]
    
    events = []
    async for e in run_agent_workflow(user_input):
        events.append(e)
    
    # Check start event
    assert events[0]["event"] == "start_of_workflow"
    
    # Check message buffering logic (Coordinator)
    # The code buffers first 2 chunks (MAX_CACHE_SIZE=2) then flushes?
    # Logic in code:
    # if len(coordinator_cache) < MAX_CACHE_SIZE:
    #     coordinator_cache.append(content)
    #     ...
    #     if len(coordinator_cache) < MAX_CACHE_SIZE: continue (buffer)
    #     else: send cached
    
    # First chunk "Hello" -> buffered (size 1) -> continue
    # Second chunk " World" -> buffered (size 2) -> flush "Hello World"
    
    assert any(e["event"] == "message" and e["data"]["delta"]["content"] == "Hello World" for e in events)

@pytest.mark.asyncio
async def test_run_agent_workflow_handoff(mock_graph):
    # Mock astream_events to yield handoff token
    async def event_generator(*args, **kwargs):
        # Coordinator says "handoff_to_planner"
        # It's split into chunks: "handoff", "_to_planner"
        yield {"event": "on_chat_model_stream", "name": "coordinator", "data": {"chunk": AIMessage(content="handoff", id="1")}, "metadata": {"checkpoint_ns": "coordinator:1"}}
        
        # This will trigger is_handoff_case = True and skip yielding message
        
        # Then some final output with messages
        yield {
            "event": "on_chain_end", 
            "name": "handoff_check", # dummy
            "data": {"output": {"messages": [AIMessage(content="Refined Plan")]}}, 
            "metadata": {}
        }

    mock_graph.astream_events = event_generator
    
    user_input = [{"role": "user", "content": "Plan please"}]
    
    events = []
    async for e in run_agent_workflow(user_input):
        events.append(e)
    
    # Verify end_of_workflow event with messages
    assert events[-1]["event"] == "end_of_workflow"
    assert len(events[-1]["data"]["messages"]) == 1
    assert events[-1]["data"]["messages"][0]["content"] == "Refined Plan"

@pytest.mark.asyncio
async def test_run_agent_workflow_empty_input():
    with pytest.raises(ValueError, match="Input could not be empty"):
        async for _ in run_agent_workflow([]):
            pass
