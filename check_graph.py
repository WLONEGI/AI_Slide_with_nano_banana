import sys
import os

# Add sources to path
sys.path.append(os.path.join(os.getcwd(), "backend/langgraph"))

try:
    from src.graph.builder import build_graph
    graph = build_graph()
    print("Graph built successfully!")
except Exception as e:
    print(f"Graph build failed: {e}")
    import traceback
    traceback.print_exc()
