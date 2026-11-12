"""Runs the real planner/researcher/analyst/critic/human_gate/writer nodes and the real worker
loop against a scripted fake chat model and a temp SQLite DB. No network, no real provider.
"""
import asyncio
import json
import uuid

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.nodes.analyst import SYSTEM_ANALYST
from app.agents.nodes.critic import SYSTEM_CRITIC
from app.agents.nodes.planner import SYSTEM_PLANNER
from app.agents.nodes.writer import SYSTEM_WRITER
from app.api.routers.audit import get_task_review
from app.core.config import settings
from app.models.agent_step import AgentStep
from app.models.base import Base
from app.models.task_run import TaskRun
from app.workers import graph_worker


class ScriptedLLM:
    critic_calls = 0
    critic_fail = False

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        sysmsg = str(messages[0].content)
        if sysmsg == SYSTEM_PLANNER:
            text, tok = json.dumps({"subtasks": ["part one", "part two"]}), (10, 5)
        elif sysmsg == SYSTEM_CRITIC:
            if ScriptedLLM.critic_fail:
                raise RuntimeError("critic backend down")
            ScriptedLLM.critic_calls += 1
            first = ScriptedLLM.critic_calls == 1
            text = json.dumps({"score": 0.4 if first else 0.9, "approved": not first,
                               "feedback": "add a comparison" if first else "", "gaps": []})
            tok = (20, 5)
        elif sysmsg == SYSTEM_ANALYST:
            text, tok = "ANALYSIS DRAFT v%d" % (ScriptedLLM.critic_calls + 1), (30, 10)
        elif sysmsg == SYSTEM_WRITER:
            text, tok = "# FINAL REPORT", (40, 10)
        else:
            text, tok = "research notes", (15, 5)
        return AIMessage(content=text, usage_metadata={
            "input_tokens": tok[0], "output_tokens": tok[1], "total_tokens": sum(tok)})


@pytest.fixture
async def env(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path/'p.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(graph_worker, "_HUMAN_POLL_INTERVAL", 0.05)
    for mod in ("planner", "researcher", "analyst", "critic", "writer"):
        monkeypatch.setattr(f"app.agents.nodes.{mod}.get_llm", lambda temperature=0.3: ScriptedLLM())
    ScriptedLLM.critic_calls = 0
    ScriptedLLM.critic_fail = False
    engine = create_async_engine(url)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _new_run(factory, hil):
    tid = uuid.uuid4()
    async with factory() as db:
        db.add(TaskRun(id=tid, original_task="Compare two sample tools", status="pending",
                       human_in_loop=hil))
        await db.commit()
    return str(tid)


async def test_review_pause_then_approve_persists_counters(env):
    tid = await _new_run(env, True)
    job = asyncio.create_task(graph_worker._run_graph_async(tid, "Compare two sample tools", True))
    for _ in range(200):
        async with env() as db:
            run = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
        if run.status == "awaiting_approval":
            break
        await asyncio.sleep(0.05)
    assert run.status == "awaiting_approval"
    # While paused: counters are already persisted, and the review shows the full latest draft.
    assert run.revision_count == 1
    assert run.total_tokens > 0 and run.total_prompt_tokens > 0 and run.total_completion_tokens > 0
    async with env() as db:
        review = await get_task_review(tid, db)
    assert review.analysis == "ANALYSIS DRAFT v2"
    assert [n.score for n in review.critic_notes] == [0.4, 0.9]
    async with env() as db:
        r = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
        r.human_decision = "approve"
        await db.commit()
    await asyncio.wait_for(job, 20)
    async with env() as db:
        run = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
        steps = list(await db.scalars(select(AgentStep).where(AgentStep.task_id == uuid.UUID(tid))))
    assert run.status == "complete" and run.final_report == "# FINAL REPORT"
    assert run.revision_count == 1
    per_step = sum(s.tokens_used for s in steps)
    assert per_step == run.total_tokens, (per_step, run.total_tokens)
    assert max(s.tokens_used for s in steps) < run.total_tokens  # deltas, not running totals


async def test_critic_failure_fails_the_run_instead_of_approving(env):
    ScriptedLLM.critic_fail = True
    tid = await _new_run(env, False)
    await asyncio.wait_for(graph_worker._run_graph_async(tid, "Compare two sample tools", False), 20)
    async with env() as db:
        run = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
    assert run.status == "failed" and not run.final_report


async def _wait_status(factory, tid, want, tries=200):
    for _ in range(tries):
        async with factory() as db:
            run = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
        if run.status == want:
            return run
        await asyncio.sleep(0.05)
    raise AssertionError(f"never reached {want}, last {run.status}")


async def _steps(factory, tid):
    async with factory() as db:
        rows = await db.scalars(select(AgentStep).where(AgentStep.task_id == uuid.UUID(tid))
                                .order_by(AgentStep.step_number))
        return [s.agent_name for s in rows]


async def test_feedback_reanalyses_once_then_waits_for_the_human_again(env):
    """Regression: a stale 'feedback' decision used to be re-read at the next pause, so the
    run looped analyst->critic->gate by itself (unbounded model calls)."""
    tid = await _new_run(env, True)
    job = asyncio.create_task(graph_worker._run_graph_async(tid, "Compare two sample tools", True))
    await _wait_status(env, tid, "awaiting_approval")
    before = await _steps(env, tid)
    assert before.count("human_gate") == 0 and before.count("analyst") == 2
    async with env() as db:
        r = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
        r.human_decision, r.human_feedback = "feedback", "Add pricing."
        await db.commit()
    for _ in range(100):  # wait for the second pause
        if (await _steps(env, tid)).count("human_gate") >= 1 and (await _steps(env, tid))[-1] == "human_gate":
            break
        await asyncio.sleep(0.05)
    await asyncio.sleep(1.0)  # a looping run would add more analyst/critic/gate steps here
    after = await _steps(env, tid)
    assert after.count("analyst") == 3 and after.count("human_gate") == 1, after
    async with env() as db:
        run = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
        assert run.status == "awaiting_approval" and not run.human_decision
        run.human_decision = "approve"
        await db.commit()
    await asyncio.wait_for(job, 20)
    async with env() as db:
        run = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
    assert run.status == "complete" and run.final_report == "# FINAL REPORT"


async def test_reject_ends_run_without_report(env):
    tid = await _new_run(env, True)
    job = asyncio.create_task(graph_worker._run_graph_async(tid, "Compare two sample tools", True))
    await _wait_status(env, tid, "awaiting_approval")
    async with env() as db:
        r = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
        r.human_decision = "reject"
        await db.commit()
    await asyncio.wait_for(job, 20)
    async with env() as db:
        run = await db.scalar(select(TaskRun).where(TaskRun.id == uuid.UUID(tid)))
    assert not run.final_report and "writer" not in await _steps(env, tid)
    assert run.status == "cancelled" and run.error == "Rejected at review."
