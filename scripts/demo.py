#!/usr/bin/env python3
"""
Critique demo — starts a task via REST API, streams SSE events, prints metrics.

Usage:
    python scripts/demo.py                   # run against localhost:8000
    python scripts/demo.py --url http://...  # run against a custom host
    python scripts/demo.py --task "..."      # custom task description
"""

import argparse
import asyncio
import json
import sys
import time

import httpx

BASE_URL = "http://localhost:8000"
DEFAULT_TASK = (
    "Research India's UPI-led fintech market and identify the top 3 "
    "investment opportunities for 2025-26, covering market size, key players "
    "such as PhonePe, Paytm and Google Pay, and the RBI/NPCI regulatory environment."
)

# ANSI colours
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
RESET = "\033[0m"


def hdr(text: str) -> str:
    return f"\n{BOLD}{CYAN}{'─' * 60}{RESET}\n{BOLD}{text}{RESET}\n{'─' * 60}"


def ok(text: str) -> str:
    return f"{GREEN}✓{RESET} {text}"


def warn(text: str) -> str:
    return f"{YELLOW}⚠{RESET} {text}"


def err(text: str) -> str:
    return f"{RED}✗{RESET} {text}"


def agent_icon(agent: str) -> str:
    icons = {
        "planner": "🗺 ",
        "researcher": "🔍",
        "analyst": "📊",
        "critic": "🔬",
        "human_gate": "👤",
        "writer": "✍️ ",
        "increment_revision": "🔄",
    }
    return icons.get(agent, "⚙️ ")


async def health_check(client: httpx.AsyncClient) -> bool:
    try:
        r = await client.get("/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


async def create_task(client: httpx.AsyncClient, task: str) -> str:
    r = await client.post("/tasks", json={"task": task}, timeout=30)
    r.raise_for_status()
    return r.json()["task_id"]


async def stream_events(client: httpx.AsyncClient, task_id: str) -> list[dict]:
    """Stream SSE events until task_complete or task_failed."""
    events = []
    t0 = time.monotonic()

    async with client.stream(
        "GET", f"/tasks/{task_id}/stream", timeout=300
    ) as response:
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                if line.startswith("event:"):
                    current_event = line[7:].strip()
                continue

            try:
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue

            event_type = data.get("event", current_event if "current_event" in dir() else "?")  # noqa
            events.append({"event": event_type, "data": data})

            elapsed = time.monotonic() - t0
            _print_event(event_type, data, elapsed)

            if event_type in ("task_complete", "task_failed"):
                break

    return events


def _print_event(event_type: str, data: dict, elapsed: float) -> None:
    ts = f"{DIM}[{elapsed:6.1f}s]{RESET}"

    if event_type == "agent_start":
        agent = data.get("agent", "?")
        step = data.get("step", "?")
        print(f"  {ts} {agent_icon(agent)} {BOLD}{agent.upper()}{RESET} starting  (step {step})")

    elif event_type == "agent_complete":
        agent = data.get("agent", "?")
        tokens = data.get("tokens", 0)
        status = data.get("status", "")
        token_str = f"{DIM} [{tokens:,} tokens]{RESET}" if tokens else ""
        status_str = f"  → {status}" if status else ""
        print(f"  {ts} {agent_icon(agent)} {agent.upper()} done{status_str}{token_str}")

    elif event_type == "agent_error":
        agent = data.get("agent", "?")
        print(f"  {ts} {agent_icon(agent)} {RED}{agent.upper()} error{RESET}")

    elif event_type == "awaiting_approval":
        score = data.get("critic_score", "N/A")
        print(f"\n  {ts} {YELLOW}⏸  AWAITING HUMAN APPROVAL{RESET}  (critic score: {score})")

    elif event_type == "task_complete":
        duration = data.get("duration_ms", 0)
        tokens = data.get("total_tokens", 0)
        print(
            f"\n{ok('TASK COMPLETE')}  "
            f"{duration / 1000:.1f}s | {tokens:,} tokens"
        )

    elif event_type == "task_failed":
        error = data.get("error", "unknown")
        print(f"\n{err('TASK FAILED')}: {error}")


async def get_task_result(client: httpx.AsyncClient, task_id: str) -> dict:
    r = await client.get(f"/tasks/{task_id}", timeout=10)
    r.raise_for_status()
    return r.json()


async def get_metrics(client: httpx.AsyncClient) -> dict:
    r = await client.get("/metrics", timeout=10)
    r.raise_for_status()
    return r.json()


def print_report(report: str | None) -> None:
    if not report:
        print(warn("No report generated."))
        return
    print(report[:3000])
    if len(report) > 3000:
        print(f"\n{DIM}... [{len(report) - 3000} more chars]{RESET}")


def print_metrics(m: dict) -> None:
    print(f"  {'Period':30s} Last {m['period_hours']}h")
    print(f"  {'Runs total':30s} {m['runs_total']}")
    print(f"  {'Successful':30s} {m['runs_successful']}  ({m['success_rate_pct']}%)")
    print(f"  {'Avg duration':30s} {m['avg_duration_ms'] / 1000:.1f}s")
    print(f"  {'P95 duration':30s} {m['p95_duration_ms'] / 1000:.1f}s")
    print(f"  {'Avg tokens / run':30s} {m['avg_tokens_per_run']:,}")
    print(f"  {'Avg revisions':30s} {m['avg_revisions']}")
    if m["agent_avg_latency_ms"]:
        print(f"\n  {'Agent avg latencies':30s}")
        for agent, ms in sorted(m["agent_avg_latency_ms"].items()):
            print(f"    {agent:28s} {ms / 1000:.1f}s")


async def main(args: argparse.Namespace) -> int:
    base_url = args.url.rstrip("/")
    task_text = args.task

    async with httpx.AsyncClient(base_url=base_url) as client:
        # ── Health check ──────────────────────────────────────────────────────
        print(hdr("Critique Demo"))
        print(f"  Target: {BOLD}{base_url}{RESET}")
        print(f"  Task:   {task_text[:80]}{'...' if len(task_text) > 80 else ''}\n")

        if not await health_check(client):
            print(err(f"Cannot reach {base_url}/health — is the server running?"))
            print("  Start it with: docker compose up -d")
            return 1
        print(ok("Server is healthy"))

        # ── Create task ───────────────────────────────────────────────────────
        print(hdr("Launching Task"))
        t_start = time.monotonic()
        task_id = await create_task(client, task_text)
        print(ok(f"Task created: {task_id}"))

        # ── Stream events ─────────────────────────────────────────────────────
        print(hdr("Agent Execution"))
        try:
            await stream_events(client, task_id)
        except httpx.ReadTimeout:
            print(warn("SSE stream timed out — fetching final state..."))

        # ── Final result ──────────────────────────────────────────────────────
        print(hdr("Final Report"))
        result = await get_task_result(client, task_id)
        print(f"  Status:         {result['status']}")
        print(f"  Revisions:      {result['revision_count']}")
        print(f"  Total tokens:   {result.get('total_tokens', 0):,}")
        if result.get("total_duration_ms"):
            print(f"  Total duration: {result['total_duration_ms'] / 1000:.1f}s")
        if result.get("critic_score"):
            print(f"  Critic score:   {result['critic_score']:.2f}")
        print()
        print_report(result.get("final_report"))

        # ── Metrics ───────────────────────────────────────────────────────────
        print(hdr("System Metrics"))
        try:
            metrics = await get_metrics(client)
            print_metrics(metrics)
        except Exception as e:
            print(warn(f"Could not fetch metrics: {e}"))

    print(f"\n{ok('Demo complete')}  wall time: {time.monotonic() - t_start:.1f}s\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Critique demo script")
    parser.add_argument(
        "--url",
        default=BASE_URL,
        help=f"Base URL of the Critique API (default: {BASE_URL})",
    )
    parser.add_argument(
        "--task",
        default=DEFAULT_TASK,
        help="Task description to run through the agent pipeline",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args)))
