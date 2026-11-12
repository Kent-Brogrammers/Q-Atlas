"""Launcher checks with fake servers and credentials; no SDK or network calls."""

import json
import os
import pty
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def launcher(tmp_path):
    root = Path(__file__).resolve().parents[3]
    shutil.copy(root / "dev.sh", tmp_path / "dev.sh")
    backend = tmp_path / "backend/.venv/bin"
    frontend = tmp_path / "frontend/node_modules/.bin"
    tools = tmp_path / "tools"
    for folder in (backend, frontend, tools):
        folder.mkdir(parents=True)
    (frontend / "vite").touch()
    (frontend / "vite").chmod(0o755)
    stub = (
        f"#!{sys.executable}\n"
        + """import json, os, sys, time
from pathlib import Path
if '-c' in sys.argv:
    sys.exit(not bool(os.environ.get('QUANTUM-KEY') or os.environ.get('QATLAS_QUANTUM_KEY')))
kind = 'backend' if '-m' in sys.argv else 'frontend'
root = Path(os.environ['TEST_LAUNCH_ROOT'])
token = os.environ.get('QUANTUM-KEY') or os.environ.get('QATLAS_QUANTUM_KEY')
record = {'has_token': bool(token), 'token_matches': token == os.environ.get('TEST_EXPECTED_TOKEN'),
          'has_instance': bool(os.environ.get('QATLAS_IBM_INSTANCE')
                               or os.environ.get('QUANTUM-CDN')),
          'compiler_aer': os.environ.get('QATLAS_ENABLE_COMPILER_AER')}
(root / (kind + '.json')).write_text(json.dumps(record))
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    if kind == 'backend' and (root / 'frontend.json').exists():
        break
    time.sleep(0.01)
"""
    )
    for path in (backend / "python", tools / "npm"):
        path.write_text(stub)
        path.chmod(0o755)
    env = os.environ.copy()
    for key in (
        "QUANTUM-KEY",
        "QUANTUM-CDN",
        "QATLAS_QUANTUM_KEY",
        "QATLAS_IBM_INSTANCE",
        "QATLAS_SKIP_QUANTUM_PROMPT",
        "QATLAS_ENABLE_COMPILER_AER",
    ):
        env.pop(key, None)
    env.update(PATH=f"{tools}:{env['PATH']}", TEST_LAUNCH_ROOT=str(tmp_path))
    return tmp_path, env


@pytest.mark.parametrize("provide_token", [True, False])
def test_interactive_start_never_prompts_and_keeps_credentials_backend_only(
    launcher, provide_token
):
    root, env = launcher
    token = "fake-$(touch NEVER_EXECUTED)-key"
    if provide_token:
        env.update({"QUANTUM-KEY": token, "QUANTUM-CDN": "fake-instance"})
    env["TEST_EXPECTED_TOKEN"] = token
    master, slave = pty.openpty()
    try:
        result = subprocess.run(
            ["bash", "-x", str(root / "dev.sh")],
            stdin=slave,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
    finally:
        os.close(master)
        os.close(slave)
    assert result.returncode == 0
    assert token not in result.stdout + result.stderr
    assert "IBM Quantum API token" not in result.stdout + result.stderr
    assert not (root / "NEVER_EXECUTED").exists()
    backend = json.loads((root / "backend.json").read_text())
    frontend = json.loads((root / "frontend.json").read_text())
    assert backend["has_token"] is provide_token
    if provide_token:
        assert backend["token_matches"] and backend["has_instance"]
    assert frontend["has_token"] is frontend["has_instance"] is False


@pytest.mark.parametrize("key_name", ["QUANTUM-KEY", "QATLAS_QUANTUM_KEY"])
def test_noninteractive_start_reuses_environment_without_frontend_leak(launcher, key_name):
    root, env = launcher
    env.update({key_name: "fake-private-token", "QATLAS_IBM_INSTANCE": "fake-instance"})
    result = subprocess.run(
        ["bash", str(root / "dev.sh")],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0
    assert "fake-private-token" not in result.stdout + result.stderr
    assert "IBM Quantum API token" not in result.stdout + result.stderr
    assert json.loads((root / "backend.json").read_text())["has_token"]
    frontend = json.loads((root / "frontend.json").read_text())
    assert frontend["has_token"] is frontend["has_instance"] is False


@pytest.mark.parametrize("setting,expected", [(None, "1"), ("0", "0")])
def test_local_compiler_execution_defaults_on_with_explicit_opt_out(launcher, setting, expected):
    root, env = launcher
    if setting is not None:
        env["QATLAS_ENABLE_COMPILER_AER"] = setting
    result = subprocess.run(
        ["bash", str(root / "dev.sh")],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0
    assert json.loads((root / "backend.json").read_text())["compiler_aer"] == expected
