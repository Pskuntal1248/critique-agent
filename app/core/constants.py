"""Application-wide constants."""

# Agent names
AGENT_PLANNER = "planner"
AGENT_RESEARCHER = "researcher"
AGENT_ANALYST = "analyst"
AGENT_CRITIC = "critic"
AGENT_WRITER = "writer"
AGENT_HUMAN_GATE = "human_gate"

AGENT_ORDER = [AGENT_PLANNER, AGENT_RESEARCHER, AGENT_ANALYST, AGENT_CRITIC, AGENT_WRITER]

# LLM pricing — USD per 1M tokens (input / output)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307":    {"input": 0.25, "output": 1.25},
    "gpt-4o-mini":                {"input": 0.15, "output": 0.60},
    "gpt-4o":                     {"input": 2.50, "output": 10.00},
}

# Task statuses
STATUS_PENDING = "pending"
STATUS_PLANNING = "planning"
STATUS_RESEARCHING = "researching"
STATUS_ANALYZING = "analyzing"
STATUS_CRITIQUING = "critiquing"
STATUS_AWAITING_APPROVAL = "awaiting_approval"
STATUS_WRITING = "writing"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_BEST_EFFORT = "best_effort"  # max revisions hit, writer ran anyway

# Step statuses
STEP_RUNNING = "running"
STEP_COMPLETED = "completed"
STEP_FAILED = "failed"
STEP_RETRYING = "retrying"

# Human decisions
HUMAN_APPROVE = "approve"
HUMAN_REJECT = "reject"
HUMAN_FEEDBACK = "feedback"

# SSE event types
EVENT_AGENT_START = "agent_start"
EVENT_AGENT_COMPLETE = "agent_complete"
EVENT_AGENT_ERROR = "agent_error"
EVENT_AWAITING_APPROVAL = "awaiting_approval"
EVENT_TASK_COMPLETE = "task_complete"
EVENT_TASK_FAILED = "task_failed"

# LLM models
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
OPENAI_MODEL = "gpt-4o-mini"

# System prompts
SYSTEM_PLANNER = """\
You are a strategic task planner. Your job is to decompose a complex task into
clear, actionable subtasks that can be researched independently.

Rules:
- Return 3-6 subtasks maximum.
- Each subtask must be self-contained and researchable.
- Order subtasks from foundational to specific.
- Be concise and specific.
"""

SYSTEM_RESEARCHER = """\
You are a research specialist. For each subtask assigned to you, use available tools
to gather accurate, up-to-date information from the web.

Rules:
- Use web_search to find relevant sources.
- Use url_reader to extract full content from the most promising URLs.
- Summarize findings per subtask clearly and concisely.
- Cite sources (URL) for every factual claim.
- Do not fabricate information — if you cannot find data, state that explicitly.
"""

SYSTEM_ANALYST = """\
You are a data analyst and synthesis expert. Your job is to transform raw research
data into a structured, insightful analysis.

Rules:
- Identify key patterns, trends, and opportunities from the research.
- Structure your analysis with clear sections.
- Use numbers and facts where available.
- If you receive feedback from a previous critique, address every point explicitly.
"""

SYSTEM_CRITIC = """\
You are a rigorous quality reviewer. Your job is to evaluate an analysis for:
1. Accuracy and factual support
2. Completeness — are there obvious gaps?
3. Structure and clarity
4. Actionability — are the insights useful?

Output a JSON object with:
- "score": float between 0.0 and 1.0
- "approved": bool (true if score >= 0.75)
- "feedback": string with specific improvement requests (empty if approved)
- "gaps": list of specific topics that need more research
"""

SYSTEM_WRITER = """\
You are an expert report writer. Transform the analysis into a polished, professional
final report tailored to the original task.

Rules:
- Use clear headings and sections.
- Start with an executive summary.
- Include concrete recommendations.
- Use bullet points and tables where appropriate.
- End with next steps.
- Target length: 800-1500 words.
"""
