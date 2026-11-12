"""Optional configuration tests use disposable files and invented credentials only."""

from app.configuration import load_quantum_env


def test_reads_hyphenated_keys_and_quoted_instance_without_expansion(tmp_path):
    marker = tmp_path / "never-executed"
    token = f"fake-$(touch {marker})-token"
    path = tmp_path / ".env"
    path.write_text(
        f'export QUANTUM-KEY="{token}" # comment\n'
        "QUANTUM-CDN='fake-instance'\n"
        "UNRELATED_SETTING=ignored\n"
    )
    env = {}
    load_quantum_env(environ=env, paths=[path])
    assert env == {"QATLAS_QUANTUM_KEY": token, "QATLAS_IBM_INSTANCE": "fake-instance"}
    assert not marker.exists()


def test_existing_environment_aliases_override_dotenv(tmp_path):
    path = tmp_path / ".env"
    path.write_text("QUANTUM-KEY=file-token\nQUANTUM-CDN=file-instance\n")
    env = {"QUANTUM-KEY": "env-token", "QATLAS_IBM_INSTANCE": "env-instance"}
    load_quantum_env(environ=env, paths=[path])
    assert env == {"QUANTUM-KEY": "env-token", "QATLAS_IBM_INSTANCE": "env-instance"}


def test_missing_empty_and_malformed_files_allow_normal_startup(tmp_path):
    path = tmp_path / ".env"
    path.write_text('QUANTUM-KEY="unterminated\nQUANTUM-CDN=\nnot an assignment\n')
    env = {}
    load_quantum_env(environ=env, paths=[tmp_path / "missing", path])
    assert env == {}
    path.write_bytes(b"\xff")
    load_quantum_env(environ=env, paths=[path])
    assert env == {}


def test_partial_configuration_and_root_priority_across_aliases(tmp_path):
    root, backend = tmp_path / "root.env", tmp_path / "backend.env"
    root.write_text("QUANTUM-CDN=root-instance\n")
    backend.write_text("QATLAS_IBM_INSTANCE=backend-instance\nQUANTUM-KEY=backend-token\n")
    env = {}
    load_quantum_env(environ=env, paths=[root, backend])
    assert env == {"QATLAS_IBM_INSTANCE": "root-instance", "QATLAS_QUANTUM_KEY": "backend-token"}


def test_explicit_empty_environment_value_is_preserved(tmp_path):
    path = tmp_path / ".env"
    path.write_text("QUANTUM-KEY=file-token\n")
    env = {"QATLAS_QUANTUM_KEY": ""}
    load_quantum_env(environ=env, paths=[path])
    assert env == {"QATLAS_QUANTUM_KEY": ""}
