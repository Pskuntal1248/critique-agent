"""Auth and ownership checks with a MOCKED Google exchange. Not real Google sign-in.

Run via tests/test_auth_isolated.py (own process and database, like the lifecycle test).
"""
import os, time
os.environ.update(GOOGLE_CLIENT_ID='cid', GOOGLE_CLIENT_SECRET='sec', AUTH_SECRET='s3cret-for-tests',
                  PUBLIC_BACKEND_URL='https://api.example', FRONTEND_URL='https://web.example')
import demo_server
from app import demo_auth
from fastapi.testclient import TestClient
import langchain_openai

class FakeChat:
    def __init__(self, **kw): pass
    def bind_tools(self, t): return self
    def invoke(self, m): raise RuntimeError('x')
langchain_openai.ChatOpenAI = FakeChat
import asyncio
import app.services.task_service as ts
ts.run_graph = demo_server.graph_worker.run_graph
async def _stub(task_id, original_task, human_in_loop): await asyncio.sleep(3600)
demo_server.graph_worker._run_graph_async = _stub

GOOD = dict(iss='https://accounts.google.com', aud='cid', exp=time.time()+600, sub='g-1',
            email='a@example.com', email_verified=True, name='Ann')
def mock(claims):
    async def f(code): return dict(claims)
    demo_auth.exchange_code = f

def login(client, claims=GOOD):
    mock(claims)
    r = client.get('/auth/google/login', follow_redirects=False)
    assert r.status_code == 302 and 'accounts.google.com' in r.headers['location']
    assert 'client_secret' not in r.headers['location']
    state = r.headers['location'].split('state=')[1].split('&')[0]
    return client.get(f'/auth/google/callback?code=c&state={state}', follow_redirects=False)

def token_of(resp):
    loc = resp.headers['location']
    assert loc.startswith('https://web.example/auth/callback#token='), loc
    return loc.split('token=')[1]

def start(client, who):
    return client.post('/tasks', json={'task': 'Compare two sample tools for a small team', 'human_in_loop': False},
        headers={'x-llm-provider': 'openai', 'x-llm-model': 'm', 'x-llm-key': 'sk-x', 'x-demo-session': who})

def test_all():
    with TestClient(demo_server.app, base_url='https://testserver') as c:
        assert c.get('/auth/config').json() == {'google': True}
        assert c.get('/auth/me').status_code == 401
        tok = token_of(login(c))
        c.cookies.clear()
        assert c.get('/auth/me', headers={'x-demo-session': tok}).json() == {'email': 'a@example.com', 'name': 'Ann'}
        # forged / tampered / expired tokens are rejected
        assert c.get('/auth/me', headers={'x-demo-session': tok[:-3] + 'abc'}).status_code == 401
        assert c.get('/auth/me', headers={'x-demo-session': 'ca1.e30.e30'}).status_code == 401
        old = demo_auth.make_session_token('g-1', 'a@example.com', 'Ann')
        real = time.time; demo_auth.time.time = lambda: real() + 31*24*3600
        assert c.get('/auth/me', headers={'x-demo-session': old}).status_code == 401
        demo_auth.time.time = real
        # bad state (no cookie), wrong audience, unverified email
        mock(GOOD); st = c.get('/auth/google/login', follow_redirects=False).headers['location'].split('state=')[1].split('&')[0]
        c.cookies.clear()
        assert 'error=state' in c.get(f'/auth/google/callback?code=c&state={st}', follow_redirects=False).headers['location']
        assert login(c, {**GOOD, 'aud': 'other'}).status_code == 400
        assert login(c, {**GOOD, 'email_verified': False}).status_code == 400
        assert login(c, {**GOOD, 'iss': 'https://evil'}).status_code == 400
        # ownership: user's task is visible to the user, not to anonymous or another user
        r = start(c, tok); assert r.status_code in (200, 201, 202), r.text
        tid = r.json()['task_id']
        time.sleep(1.0)
        assert c.get(f'/tasks/{tid}', headers={'x-demo-session': tok}).status_code == 200
        assert c.get(f'/tasks/{tid}', headers={'x-demo-session': 'anon-1'}).status_code == 404
        tok2 = token_of(login(c, {**GOOD, 'sub': 'g-2', 'email': 'b@example.com'}))
        assert c.get(f'/tasks/{tid}', headers={'x-demo-session': tok2}).status_code == 404
        assert c.get(f'/tasks/{tid}', headers={'x-demo-session': 'ca1.' + tok.split('.',1)[1][:-2] + 'zz'}).status_code == 404
        ids = [t['task_id'] for t in c.get('/tasks', headers={'x-demo-session': tok}).json()]
        assert tid in ids
        assert c.get('/tasks', headers={'x-demo-session': tok2}).json() == []
        # restart simulation: memory cache lost, database still knows the owner
        demo_server._owners.clear()
        assert c.get(f'/tasks/{tid}', headers={'x-demo-session': tok}).status_code == 200
        assert c.get(f'/tasks/{tid}', headers={'x-demo-session': tok2}).status_code == 404
        # unsigned session ids still work for anonymous runs
        r = start(c, 'anon-1'); assert r.status_code in (200, 201, 202)

def test_disabled_when_unconfigured():
    for k in ('GOOGLE_CLIENT_SECRET',): os.environ.pop(k)
    with TestClient(demo_server.app, base_url='https://testserver') as c:
        assert c.get('/auth/config').json() == {'google': False}
        assert c.get('/auth/google/login', follow_redirects=False).status_code == 503
        tok = demo_auth.TOKEN_PREFIX + 'x.y'
        assert start(c, tok).status_code == 400
