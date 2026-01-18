# Project Overview

**Project Name:** Spell (formerly Lang Manus)
**Description:** A community-driven AI automation framework that uses a hierarchical multi-agent system to coordinate specialized agents (Coordinator, Planner, Supervisor, Researcher, Coder, Browser, Reporter) for complex tasks.
**Frameworks & Tools:**
- **LangGraph**: For agent workflow.
- **FastAPI**: For the API server.
- **uv**: For Python package management.
- **LLMs**: Support for Vertex AI (Gemini) and OpenAI-compatible APIs.
- **Search**: Tavily and Jina.
**Key Directories:**
- `backend/langgraph`: Main source code.
- `backend/langgraph/src`: Core logic, agents, tools.
- `backend/langgraph/src/prompts`: Agent prompts (markdown templates).
