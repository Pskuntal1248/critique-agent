"""Shared state definition for the Critique LangGraph graph."""

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Identity
    task_id: str
    original_task: str

    # Planner output
    subtasks: list[str]

    # Researcher output — list of {subtask, query, sources: [{url, title, content}]}
    research_results: list[dict]

    # Analyst output
    analysis: str

    # Critic output
    critic_score: float
    critic_feedback: str
    critic_approved: bool

    # Revision tracking
    revision_count: int

    # Human-in-the-loop
    human_in_loop: bool
    human_decision: str | None   # "approve" | "reject" | "feedback"
    human_feedback: str | None

    # Writer output
    final_report: str | None

    # Pipeline control
    status: str
    active_agent: str
    tokens_used: int
    prompt_tokens_used: int       # input/prompt tokens (for cost calc)
    completion_tokens_used: int   # output/completion tokens (for cost calc)
    errors: Annotated[list[str], lambda a, b: a + b]  # append-only

    # LangChain message history (auto-merged by add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]
