
import os
import sys
import pytest
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Fallback API Key logic (same as Phase 1)
if os.getenv("GOOGLE_API_KEY"):
    google_key = os.getenv("GOOGLE_API_KEY")
    for key in ["BASIC_API_KEY", "REASONING_API_KEY", "HIGH_REASONING_API_KEY", "VL_API_KEY"]:
        if not os.getenv(key):
            os.environ[key] = google_key

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

@pytest.fixture
def mock_graph_state():
    """Returns a basic initial state for integration testing."""
    from langchain_core.messages import HumanMessage
    return {
        "messages": [HumanMessage(content="Test Input", name="user")],
        "plan": [],
        "artifacts": {},
        "current_step_index": 0,
        "retry_count": 0,
        "feedback_history": {}
    }
