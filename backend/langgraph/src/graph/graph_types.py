from typing import Literal, TypedDict, Any, List, Annotated
import operator
from langgraph.graph import MessagesState


from src.schemas.design import DesignContext
from src.schemas.outputs import ResearchTask, ResearchResult



class TaskStep(TypedDict):
    """A single step in the execution plan."""
    id: int
    role: str  # The worker to execute this step (e.g., 'storywriter', 'coder')
    instruction: str  # Specific instruction for the worker
    description: str  # Brief description of the step


class State(MessagesState):
    """State for the agent system, extends MessagesState."""

    # Constants
    TEAM_MEMBERS: list[str]

    # Runtime Variables
    plan: list[TaskStep]
    current_step_index: int
    artifacts: dict[str, Any]  # Store outputs from workers (text, charts, etc.)
    
    # Legacy/Planner Controls
    deep_thinking_mode: bool
    search_before_planning: bool

    # New: Control Flow & Quality Assurance
    feedback_history: dict[str, list[str]]
    retry_count: int
    current_quality_score: float         # Latest Review Score
    error_context: str | None            # Context for replanning
    replanning_count: int                # Count of replanning triggered

    # Explicit State Logic (Added during Refactoring)
    review_status: Literal["approved", "rejected", "pending"] | None
    
    # NEW: PPTXテンプレートデザインコンテキスト
    design_context: DesignContext | None

    # NEW: Parallel Research Tasks
    research_tasks: List[ResearchTask]
    research_results: Annotated[List[ResearchResult], operator.add]

