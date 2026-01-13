from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from .graph_types import State
from .nodes import (
    supervisor_node,
    research_node,
    research_node,
    coordinator_node,

    storywriter_node,
    visualizer_node,
    planner_node,
    data_analyst_node,
    reviewer_node,
)


def build_graph(checkpointer=None):
    """Build and return the agent workflow graph.
    
    Args:
        checkpointer: Optional persistence checkpointer (e.g. MemorySaver, AsyncPostgresSaver)
    """
    builder = StateGraph(State)
    builder.add_edge(START, "coordinator")
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("planner", planner_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("researcher", research_node)

    builder.add_node("storywriter", storywriter_node)
    builder.add_node("visualizer", visualizer_node)
    builder.add_node("data_analyst", data_analyst_node)
    builder.add_node("reviewer", reviewer_node)

    return builder.compile(checkpointer=checkpointer)

