import logging
import uuid
from typing import Any, AsyncGenerator

from langchain_community.adapters.openai import convert_message_to_dict
from langgraph.checkpoint.memory import MemorySaver

from src.config.env import POSTGRES_DB_URI
from src.config import TEAM_MEMBERS
from src.config.settings import settings
from src.graph import build_graph

# Try importing Postgres dependencies
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool
    HAS_POSTGRES_DEPS = True
except ImportError:
    HAS_POSTGRES_DEPS = False


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)



class WorkflowManager:
    """
    Singleton manager for the LangGraph workflow and its resources (DB connection, Graph instance).
    Eliminates global variables and ensures safe initialization/cleanup.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
            cls._instance.pool = None
            cls._instance.graph = None
        return cls._instance

    async def initialize(self):
        """
        Initialize the graph with appropriate checkpointer.
        Idempotent: Safe to call multiple times, though usually called once at startup.
        """
        if self.initialized:
            logger.info("WorkflowManager already initialized.")
            return

        logger.info("Initializing WorkflowManager...")

        if POSTGRES_DB_URI:
            if not HAS_POSTGRES_DEPS:
                error_msg = (
                    "POSTGRES_DB_URI is set but postgres dependencies "
                    "(langgraph-checkpoint-postgres, psycopg_pool) are missing. "
                    "Cannot establish persistence."
                )
                logger.critical(error_msg)
                raise ImportError(error_msg)

            logger.info("Initializing Postgres Checkpointer...")
            try:
                # Create connection pool
                connection_info = POSTGRES_DB_URI.replace("postgresql+psycopg://", "postgresql://")
                
                # Cloud Run / Serverless optimized pool settings
                self.pool = AsyncConnectionPool(
                    conninfo=connection_info,  
                    min_size=1, 
                    max_size=10, 
                    open=False,
                    timeout=30.0
                )
                await self.pool.open()
                
                # Setup checkpointer
                checkpointer = AsyncPostgresSaver(self.pool)
                await checkpointer.setup()
                
                # Build graph
                self.graph = build_graph(checkpointer=checkpointer)
                logger.info("✅ Graph initialized with AsyncPostgresSaver. Persistence enabled.")
                
            except Exception as e:
                logger.critical(f"❌ Failed to initialize Postgres persistence: {e}")
                logger.critical("Aborting startup to prevent state loss.")
                if self.pool:
                    await self.pool.close()
                raise e
        else:
            logger.warning("⚠️ POSTGRES_DB_URI not set. Using MemorySaver (Non-persistent). State will be lost on restart.")
            self.graph = build_graph(checkpointer=MemorySaver())

        self.initialized = True

    async def close(self):
        """Cleanup resources."""
        if self.pool:
            logger.info("Closing DB connection pool...")
            await self.pool.close()
            self.pool = None
        self.initialized = False
        logger.info("WorkflowManager shutdown complete.")

    def get_graph(self):
        """Return the initialized graph instance."""
        if not self.graph:
            raise RuntimeError("Graph not initialized. Call initialize() first.")
        return self.graph


# Expose singleton instance methods for existing API compatibility
_manager = WorkflowManager()

async def initialize_graph():
    await _manager.initialize()

async def close_graph():
    await _manager.close()

async def run_agent_workflow(
    user_input_messages: list[dict[str, Any]],
    debug: bool = False,
    deep_thinking_mode: bool = False,
    search_before_planning: bool = False,
    thread_id: str | None = None,
    design_context: Any = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run the agent workflow with the given user input."""
    if not user_input_messages:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    # Get graph from manager
    graph = _manager.get_graph()

    # Use provided thread_id or generate a new one
    if not thread_id:
        thread_id = str(uuid.uuid4())

    logger.info(f"Starting workflow with user input: {user_input_messages} (Thread ID: {thread_id})")
    
    if design_context:
        logger.info(f"DesignContext provided: {len(design_context.layouts)} layouts")

    # Workflow ID identifies this specific execution run (for logging tools/agents)
    # Note: thread_id is for persistence, workflow_id is for trace/log uniqueness of this run.
    workflow_id = str(uuid.uuid4())

    streaming_llm_agents = [*TEAM_MEMBERS, "planner", "coordinator"]

    # Thread-safe local variables for coordinator logic
    coordinator_cache: list[str] = []
    is_handoff_case: bool = False
    
    # Configure persistence
    config = {"configurable": {"thread_id": thread_id}}

    input_state = {
        "TEAM_MEMBERS": TEAM_MEMBERS,
        "messages": user_input_messages,
        "deep_thinking_mode": deep_thinking_mode,
        "search_before_planning": search_before_planning,
        "design_context": design_context,
    }

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
            yield_payload = {
                "event": "start_of_agent",
                "data": {
                    "agent_name": name,
                    "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                },
            }
        elif kind == "on_chain_end" and name in streaming_llm_agents:
            yield_payload = {
                "event": "end_of_agent",
                "data": {
                    "agent_name": name,
                    "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                },
            }
        elif kind == "on_chat_model_start" and node in streaming_llm_agents:
            yield_payload = {
                "event": "start_of_llm",
                "data": {"agent_name": node},
            }
        elif kind == "on_chat_model_end" and node in streaming_llm_agents:
            yield_payload = {
                "event": "end_of_llm",
                "data": {"agent_name": node},
            }
        elif kind == "on_chat_model_stream" and node in streaming_llm_agents:
            content = data["chunk"].content
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                    elif hasattr(part, "text"):
                        text_parts.append(part.text)
                content = "".join(text_parts)

            if content is None or content == "":
                if not data["chunk"].additional_kwargs.get("reasoning_content"):
                    continue
                yield_payload = {
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
                if node == "coordinator":
                    if len(coordinator_cache) < settings.MAX_COORD_CACHE_SIZE:
                        coordinator_cache.append(content)
                        cached_content = "".join(coordinator_cache)
                        if cached_content.startswith("handoff"):
                            is_handoff_case = True
                            continue
                        if len(coordinator_cache) < settings.MAX_COORD_CACHE_SIZE:
                            continue
                        yield_payload = {
                            "event": "message",
                            "data": {
                                "message_id": data["chunk"].id,
                                "delta": {"content": cached_content},
                            },
                        }
                    elif not is_handoff_case:
                        yield_payload = {
                            "event": "message",
                            "data": {
                                "message_id": data["chunk"].id,
                                "delta": {"content": content},
                            },
                        }
                else:
                    yield_payload = {
                        "event": "message",
                        "data": {
                            "message_id": data["chunk"].id,
                            "delta": {"content": content},
                        },
                    }
        elif kind == "on_tool_start" and node in TEAM_MEMBERS:
            yield_payload = {
                "event": "tool_call",
                "data": {
                    "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                    "tool_name": name,
                    "tool_input": data.get("input"),
                },
            }
        elif kind == "on_tool_end" and node in TEAM_MEMBERS:
            yield_payload = {
                "event": "tool_call_result",
                "data": {
                    "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                    "tool_name": name,
                    "tool_result": data["output"].content if data.get("output") else "",
                },
            }
        else:
            continue
        yield yield_payload

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
