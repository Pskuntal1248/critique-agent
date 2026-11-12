"""Local regression check: does the BYOK wrapper release credentials when a run ends?

Scope: demo_server request/job wrapper with a stub run coroutine. It does NOT run the real
LangGraph nodes. It checks that the object holding the key (a fake chat client that records
its api_key) is garbage collected after success, error, cancel and timeout, and that the
key never lands in the SQLite file.
"""
import asyncio, gc, os, weakref, tempfile, sqlite3
DBDIR = os.path.dirname(os.environ['DATABASE_URL'].split('///')[1])
import pytest
import demo_server
from fastapi.testclient import TestClient
import langchain_openai

SENTINEL = 'sk-SENTINEL-1234567890'
clients = []

class FakeChat:
    def __init__(self, **kw):
        self.api_key = kw['api_key']
        clients.append(weakref.ref(self))
    def bind_tools(self, t): return self
    def invoke(self, m): raise RuntimeError('boom ' + self.api_key)

def alive():
    gc.collect(); gc.collect()
    return [c for c in clients if c() is not None]

def post(client, mode):
    async def stub(task_id, original_task, human_in_loop):
        llm = demo_server.byok_llm()  # the run keeps its client (and key) in a local, as the graph nodes do while running
        if mode == 'ok': return
        if mode == 'error': raise RuntimeError('fail')
        await asyncio.sleep(3600)  # abandoned human review / hang
    demo_server.graph_worker._run_graph_async = stub
    return client.post('/tasks', json={'task': 'Sample task for lifecycle test'}, headers={
        'x-llm-provider': 'openai', 'x-llm-model': 'm', 'x-llm-key': SENTINEL, 'x-demo-session': 's1'})

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(langchain_openai, 'ChatOpenAI', FakeChat)
    import app.services.task_service as ts
    monkeypatch.setattr(ts, 'run_graph', demo_server.graph_worker.run_graph)  # conftest imported app before demo_server patched it
    monkeypatch.setattr(ts, 'celery_app', None, raising=False)
    clients.clear()
    with TestClient(demo_server.app) as c:
        yield c

def run_and_wait(client, mode, cancel=False, timeout_patch=None):
    r = post(client, mode)
    assert r.status_code in (200, 201, 202), r.text
    tid = r.json()['task_id']
    import time; time.sleep(0.5)
    return tid

def test_success_releases_key(client):
    run_and_wait(client, 'ok'); assert alive() == []
    assert not demo_server._jobs

def test_error_releases_key(client):
    run_and_wait(client, 'error'); assert alive() == []
    assert not demo_server._jobs

def test_cancel_releases_key(client):
    tid = run_and_wait(client, 'hang')
    assert demo_server._jobs.get(tid) is not None
    client.portal.call(demo_server._jobs[tid].cancel)  # cancel on the app's own event loop
    import time; time.sleep(0.5)
    assert alive() == [] and not demo_server._jobs

def test_hang_holds_key_until_cutoff(client):
    # Documents current behaviour: an abandoned run keeps the key until the 600 s cutoff.
    tid = run_and_wait(client, 'hang')
    assert len(alive()) == 1 and tid in demo_server._jobs
    client.portal.call(demo_server._jobs[tid].cancel)

def test_key_not_in_sqlite_or_response(client):
    r = post(client, 'ok'); assert SENTINEL not in r.text
    import time; time.sleep(0.5)
    for f in os.listdir(DBDIR):
        p = os.path.join(DBDIR, f)
        assert SENTINEL.encode() not in open(p, 'rb').read()

def test_error_key_eventually_released_diagnostic(client):
    run_and_wait(client, 'error')
    import time
    for _ in range(6):
        time.sleep(0.5)
        if not alive(): return
    import gc
    live = alive()
    refs = [type(r).__name__ for o in live for r in gc.get_referrers(o())]
    raise AssertionError(f'still alive; referrers: {refs}')


def test_review_endpoint_is_session_scoped(client):
    tid = run_and_wait(client, 'ok')
    h = lambda s: {'x-demo-session': s}
    assert client.get(f'/tasks/{tid}/review', headers=h('s1')).status_code == 200
    assert client.get(f'/tasks/{tid}/review', headers=h('other')).status_code == 404
    assert client.get(f'/tasks/{tid}/review').status_code == 404


def _status(client, tid, session='s1'):
    return client.get(f'/tasks/{tid}', headers={'x-demo-session': session}).json()


def test_timeout_marks_run_failed_and_releases_key(client, monkeypatch):
    monkeypatch.setattr(demo_server, 'JOB_TIMEOUT_SECONDS', 0.3)
    tid = run_and_wait(client, 'hang')  # sleeps 0.5 s, past the 0.3 s cap
    import time; time.sleep(0.5)
    body = _status(client, tid)
    assert body['status'] == 'failed' and 'review counts toward this limit' in (body.get('error') or '')
    assert alive() == [] and not demo_server._jobs


def test_review_wait_counts_toward_cap_and_never_auto_approves(client, monkeypatch):
    """Real nodes and worker loop, scripted model: the run pauses at review, nobody answers,
    and the cap fails the run. It must not be approved or write a report."""
    from tests.test_pipeline_integration import ScriptedLLM
    monkeypatch.setattr(langchain_openai, 'ChatOpenAI', lambda **kw: ScriptedLLM())
    ScriptedLLM.critic_calls = 0; ScriptedLLM.critic_fail = False
    monkeypatch.setattr(demo_server, 'JOB_TIMEOUT_SECONDS', 6)
    monkeypatch.setattr(demo_server.graph_worker, '_run_graph_async', _REAL_RUN)
    r = client.post('/tasks', json={'task': 'Compare two sample tools', 'human_in_loop': True}, headers={
        'x-llm-provider': 'openai', 'x-llm-model': 'm', 'x-llm-key': SENTINEL, 'x-demo-session': 's1'})
    tid = r.json()['task_id']
    import time
    seen = set()
    for _ in range(40):
        time.sleep(0.5); st = _status(client, tid); seen.add(st['status'])
        if st['status'] == 'failed': break
    assert 'awaiting_approval' in seen
    st = _status(client, tid)
    assert st['status'] == 'failed' and not st.get('final_report')
    assert 'review counts toward this limit' in (st.get('error') or '')
    assert st['llm_provider'] == 'openai'
    time.sleep(0.5); assert alive() == [] and not demo_server._jobs


_REAL_RUN = demo_server.graph_worker._run_graph_async


def test_cancel_stops_further_model_calls(client, monkeypatch):
    """Cancel through the real API while the real worker is mid-run: model calls must stop."""
    import threading, time
    from tests.test_pipeline_integration import ScriptedLLM
    calls = []
    class Slow(ScriptedLLM):
        def invoke(self, messages):
            calls.append(time.monotonic()); time.sleep(0.4)
            return super().invoke(messages)
    monkeypatch.setattr(langchain_openai, 'ChatOpenAI', lambda **kw: Slow())
    ScriptedLLM.critic_calls = 0; ScriptedLLM.critic_fail = False
    monkeypatch.setattr(demo_server.graph_worker, '_run_graph_async', _REAL_RUN)
    r = client.post('/tasks', json={'task': 'Compare two sample tools', 'human_in_loop': False}, headers={
        'x-llm-provider': 'openai', 'x-llm-model': 'm', 'x-llm-key': SENTINEL, 'x-demo-session': 's1'})
    tid = r.json()['task_id']
    time.sleep(1.0)
    assert calls, 'run never started calling the model'
    c = client.post(f'/tasks/{tid}/cancel', headers={'x-demo-session': 's1'})
    assert c.status_code == 200 and c.json()['status'] == 'cancelled'
    time.sleep(1.0)  # let any call already in flight finish
    n = len(calls)
    time.sleep(3.0)
    assert len(calls) == n, 'model calls continued after cancel'
    assert _status(client, tid)['status'] == 'cancelled'
    assert alive() == [] and not demo_server._jobs
    # another session cannot cancel it
    assert client.post(f'/tasks/{tid}/cancel', headers={'x-demo-session': 'other'}).status_code == 404
