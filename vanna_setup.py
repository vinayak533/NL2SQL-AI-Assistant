

import os
from dotenv import load_dotenv

load_dotenv()

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool, SaveTextMemoryTool
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.google import GeminiLlmService  # Option A — Google Gemini

DB_PATH = os.getenv("DB_PATH", "clinic.db")


# ── User resolver ──────────────────────────────────────────────────────────────

class SimpleUserResolver(UserResolver):
    """Identifies every incoming request as the same default user."""

    async def resolve_user(self, request_context: RequestContext) -> User:
        email = (
            request_context.get_cookie("vanna_email")
            or request_context.get_header("X-User-Email")
            or "default@clinic.local"
        )
        group = "admin" if email == "admin@clinic.local" else "user"
        return User(id=email, email=email, group_memberships=[group])


# ── Agent memory ───────────────────────────────────────────────────────────────

agent_memory = DemoAgentMemory(max_items=1000)


# ── Tool registry ──────────────────────────────────────────────────────────────

def build_tool_registry() -> ToolRegistry:
    tools = ToolRegistry()

    # SQL execution tool
    tools.register_local_tool(
        RunSqlTool(sql_runner=SqliteRunner(database_path=DB_PATH)),
        access_groups=["admin", "user"],
    )

    # Visualisation tool (Plotly charts)
    tools.register_local_tool(
        VisualizeDataTool(),
        access_groups=["admin", "user"],
    )

    # Memory tools — let the agent save & search past Q-SQL pairs
    tools.register_local_tool(
        SaveQuestionToolArgsTool(),
        access_groups=["admin", "user"],
    )
    tools.register_local_tool(
        SearchSavedCorrectToolUsesTool(),
        access_groups=["admin", "user"],
    )
    tools.register_local_tool(
        SaveTextMemoryTool(),
        access_groups=["admin", "user"],
    )

    return tools


# ── LLM service ────────────────────────────────────────────────────────────────

def build_llm_service() -> GeminiLlmService:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY is not set. Add it to your .env file."
        )
    return GeminiLlmService(
        model="gemini-2.5-flash",
        api_key=api_key,
    )


# ── Agent factory ──────────────────────────────────────────────────────────────

def create_agent() -> Agent:
    """Build and return the fully configured Vanna 2.0 Agent."""
    llm      = build_llm_service()
    tools    = build_tool_registry()
    resolver = SimpleUserResolver()

    agent = Agent(
        llm_service=llm,
        tool_registry=tools,
        user_resolver=resolver,
        agent_memory=agent_memory,
        config=AgentConfig(),
    )
    return agent


# ── Singleton (imported by main.py and seed_memory.py) ────────────────────────

_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent
