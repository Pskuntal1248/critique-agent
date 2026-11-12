import os, subprocess, sys, tempfile

def test_auth_mocked():
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{d}/auth.db"}
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/authsuite/test_auth_mocked.py", "-q", "-x", "-p", "no:cacheprovider"],
                           env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1000:]
