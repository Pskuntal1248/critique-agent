"""Runs tests/lifecycle in a fresh interpreter with normal logging and log capture ON."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_byok_lifecycle_suite_in_isolated_process():
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{d}/lifecycle.db"}
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/lifecycle", "-q", "-p", "no:cacheprovider",
             "--confcutdir=tests/lifecycle", "--rootdir", str(root)],
            cwd=root, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
