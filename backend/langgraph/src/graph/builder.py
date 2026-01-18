from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from .graph_types import State
from .nodes import (
    supervisor_node,
    supervisor_node,
    research_node, # Keep for safety, though replaced in graph
    research_dispatcher_node,
    research_worker_node,
    research_aggregator_node,
    fan_out_research,
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
    
    # Parallel Researcher: Map 'researcher' role to dispatcher
    builder.add_node("researcher", research_dispatcher_node)
    builder.add_node("research_worker", research_worker_node)
    builder.add_node("research_aggregator", research_aggregator_node)

    # Fan-out from Dispatcher (researcher) -> Workers
    builder.add_conditional_edges("researcher", fan_out_research, ["research_worker"])
    
    # Workers -> Aggregator
    builder.add_edge("research_worker", "research_aggregator")


    builder.add_node("storywriter", storywriter_node)
    builder.add_node("visualizer", visualizer_node)
    builder.add_node("data_analyst", data_analyst_node)
    builder.add_node("reviewer", reviewer_node)

    return builder.compile(checkpointer=checkpointer)

