import logging

from src.config import TEAM_MEMBERS
from src.graph import build_graph
from langchain_community.adapters.openai import convert_message_to_dict
from langgraph.checkpoint.memory import MemorySaver
import uuid
from typing import Final, AsyncGenerator, Any

from src.config.env import POSTGRES_DB_URI

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool
    HAS_POSTGRES_DEPS = True
except ImportError:
    HAS_POSTGRES_DEPS = False
    logger = logging.getLogger(__name__)
    if POSTGRES_DB_URI:
        logger.warning("POSTGRES_DB_URI is set but postgres dependencies (langgraph-checkpoint-postgres, psycopg_pool) are missing.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

# Global instances
graph = build_graph(checkpointer=MemorySaver()) # Default fallback
_pool = None

async def initialize_graph():
    """Initialize the graph with appropriate checkpointer."""
    global graph, _pool
    
    if POSTGRES_DB_URI and HAS_POSTGRES_DEPS:
        logger.info("Initializing Postgres Checkpointer...")
        try:
            # Create connection pool
            # psycopg expects postgresql:// scheme, not sqlalchemy's postgresql+psycopg://
            conn_info = POSTGRES_DB_URI.replace("postgresql+psycopg://", "postgresql://")
            _pool = AsyncConnectionPool(conninfo=conn_info, min_size=1, max_size=10, open=False)
            await _pool.open()
            
            # Setup checkpointer
            checkpointer = AsyncPostgresSaver(_pool)
            await checkpointer.setup()
            
            # Build graph with postgres checkpointer
            graph = build_graph(checkpointer=checkpointer)
            logger.info("Graph initialized with AsyncPostgresSaver.")
        except Exception as e:
            logger.error(f"Failed to initialize Postgres persistence: {e}")
            logger.warning("Falling back to MemorySaver.")
            graph = build_graph(checkpointer=MemorySaver())
    else:
        logger.info("Using MemorySaver (Non-persistent).")
        graph = build_graph(checkpointer=MemorySaver())

async def close_graph():
    """Cleanup resources."""
    global _pool
    if _pool:
        await _pool.close()


# Cache for coordinator messages

# Cache for coordinator messages - Removed globals to ensure thread safety
from src.config.settings import settings



async def run_agent_workflow(
    user_input_messages: list[dict[str, Any]],
    debug: bool = False,
    deep_thinking_mode: bool = False,
    search_before_planning: bool = False,
    thread_id: str | None = None,
):
    """Run the agent workflow with the given user input.

    Args:
        user_input_messages: The user request messages (list of dicts).
        debug: If True, enables debug level logging.
        deep_thinking_mode: Whether to enable extended reasoning.
        search_before_planning: Whether to perform an initial search before planning.
        thread_id: Identifier for the conversation thread (persistence).

    Yields:
        dict: A dictionary containing event data with the following structure:
            - event (str): Event type (e.g., 'start_of_workflow', 'message', 'tool_call').
            - data (dict): Event payload.
    """
    if not user_input_messages:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    # Use provided thread_id or generate a new one
    if not thread_id:
        thread_id = str(uuid.uuid4())

    logger.info(f"Starting workflow with user input: {user_input_messages} (Thread ID: {thread_id})")

    # Workflow ID identifies this specific execution run
    workflow_id = str(uuid.uuid4())

    streaming_llm_agents = [*TEAM_MEMBERS, "planner", "coordinator"]

    # Reset coordinator cache at the start of each workflow
    # Use local variables for thread safety
    coordinator_cache: list[str] = []
    is_handoff_case: bool = False
    
    # Configure persistence
    config = {"configurable": {"thread_id": thread_id}}

    # When a thread_id is present, passing 'messages' in the input dict
    # will APPEND to the existing message history in the state (due to MessagesState reducer).
    # This triggers the graph to start from the entry point (coordinator) again,
    # but with the full context (past conversation + new user instruction).
    input_state = {
        # Constants
        "TEAM_MEMBERS": TEAM_MEMBERS,
        # Runtime Variables
        "messages": user_input_messages,
        "deep_thinking_mode": deep_thinking_mode,
        "search_before_planning": search_before_planning,
    }

    # TODO: extract message content from object, specifically for on_chat_model_stream
    async for event in graph.astream_events(
        input_state,
        config=config,
        version="v2",
    ):
        kind = event.get("event")
        data = event.get("data")
        name = event.get("name")
        metadata = event.get("metadata")
        node = (
            ""
            if (metadata.get("checkpoint_ns") is None)
            else metadata.get("checkpoint_ns").split(":")[0]
        )
        langgraph_step = (
            ""
            if (metadata.get("langgraph_step") is None)
            else str(metadata["langgraph_step"])
        )
        run_id = "" if (event.get("run_id") is None) else str(event["run_id"])

        if kind == "on_chain_start" and name in streaming_llm_agents:
            if name == "planner":
                yield {
                    "event": "start_of_workflow",
                    "data": {
                        "workflow_id": workflow_id, 
                        "thread_id": thread_id,
                        "input": user_input_messages
                    },
                }
            ydata = {
                "event": "start_of_agent",
                "data": {
                    "agent_name": name,
                    "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                },
            }
        elif kind == "on_chain_end" and name in streaming_llm_agents:
            ydata = {
                "event": "end_of_agent",
                "data": {
                    "agent_name": name,
                    "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                },
            }
        elif kind == "on_chat_model_start" and node in streaming_llm_agents:
            ydata = {
                "event": "start_of_llm",
                "data": {"agent_name": node},
            }
        elif kind == "on_chat_model_end" and node in streaming_llm_agents:
            ydata = {
                "event": "end_of_llm",
                "data": {"agent_name": node},
            }
        elif kind == "on_chat_model_stream" and node in streaming_llm_agents:
            content = data["chunk"].content
            if content is None or content == "":
                if not data["chunk"].additional_kwargs.get("reasoning_content"):
                    # Skip empty messages
                    continue
                ydata = {
                    "event": "message",
                    "data": {
                        "message_id": data["chunk"].id,
                        "delta": {
                            "reasoning_content": (
                                data["chunk"].additional_kwargs["reasoning_content"]
                            )
                        },
                    },
                }
            else:
                # Check if the message is from the coordinator
                if node == "coordinator":
                    if len(coordinator_cache) < settings.MAX_COORD_CACHE_SIZE:
                        coordinator_cache.append(content)
                        cached_content = "".join(coordinator_cache)
                        if cached_content.startswith("handoff"):
                            is_handoff_case = True
                            continue
                        if len(coordinator_cache) < settings.MAX_COORD_CACHE_SIZE:
                            continue
                        # Send the cached message
                        ydata = {
                            "event": "message",
                            "data": {
                                "message_id": data["chunk"].id,
                                "delta": {"content": cached_content},
                            },
                        }
                    elif not is_handoff_case:
                        # For other agents, send the message directly
                        ydata = {
                            "event": "message",
                            "data": {
                                "message_id": data["chunk"].id,
                                "delta": {"content": content},
                            },
                        }
                else:
                    # For other agents, send the message directly
                    ydata = {
                        "event": "message",
                        "data": {
                            "message_id": data["chunk"].id,
                            "delta": {"content": content},
                        },
                    }
        elif kind == "on_tool_start" and node in TEAM_MEMBERS:
            ydata = {
                "event": "tool_call",
                "data": {
                    "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                    "tool_name": name,
                    "tool_input": data.get("input"),
                },
            }
        elif kind == "on_tool_end" and node in TEAM_MEMBERS:
            ydata = {
                "event": "tool_call_result",
                "data": {
                    "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                    "tool_name": name,
                    "tool_result": data["output"].content if data.get("output") else "",
                },
            }
        else:
            continue
        yield ydata

    if is_handoff_case:
        yield {
            "event": "end_of_workflow",
            "data": {
                "workflow_id": workflow_id,
                "messages": [
                    convert_message_to_dict(msg)
                    for msg in data["output"].get("messages", [])
                ],
            },
        }
