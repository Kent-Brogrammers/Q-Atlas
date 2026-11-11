#!/usr/bin/env bash
# Never trace credential input or environment assignments, including under bash -x.
set +x
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if (( BASH_VERSINFO[0] < 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] < 3) )); then
    printf 'Use Bash 4.3 or newer to run dev.sh.\n' >&2
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    printf 'npm is missing. Install Node.js first; see README.md.\n' >&2
    exit 1
fi
if [[ ! -x "$PROJECT_ROOT/backend/.venv/bin/python" ]]; then
    printf 'Backend environment missing. Run uv sync --locked in backend/ first.\n' >&2
    exit 1
fi
if [[ ! -x "$PROJECT_ROOT/frontend/node_modules/.bin/vite" ]]; then
    printf 'Frontend dependencies missing. Run npm ci in frontend/ first.\n' >&2
    exit 1
fi

# Prompt only in a terminal. Empty input skips credentials; CI/piped startup never waits.
# Token text is read as data, is never evaluated, and is exported only in the backend child.
qatlas_prompt_token=''
qatlas_prompt_instance=''
if [[ -t 0 && "${QATLAS_SKIP_QUANTUM_PROMPT:-0}" != 1 ]]; then
    printf 'Quantum setup is optional. Startup never connects or submits jobs.\n'
    qatlas_has_key=0
    if "$PROJECT_ROOT/backend/.venv/bin/python" -c 'import os, sys; sys.exit(not bool((os.environ.get("QUANTUM-KEY") or os.environ.get("QATLAS_QUANTUM_KEY") or "").strip()))'; then
        qatlas_has_key=1
        printf 'Quantum token already provided by your environment.\n'
    else
        IFS= read -r -s -p 'IBM Quantum API token (hidden; Enter to skip): ' qatlas_prompt_token
        printf '\n'
    fi
    if [[ "$qatlas_has_key" == 1 || -n "$qatlas_prompt_token" ]]; then
        if [[ -z "${QATLAS_IBM_INSTANCE:-}" ]]; then
            IFS= read -r -p 'IBM instance name or CRN (Enter to leave unconfigured): ' qatlas_prompt_instance
        fi
        printf 'Quantum settings will be available to the backend only; nothing is saved.\n'
    fi
fi

server_pids=()
cleanup() {
    trap - EXIT
    trap '' INT TERM
    for pid in "${server_pids[@]}"; do
        kill -TERM -- "-$pid" 2>/dev/null || true
    done
    wait "${server_pids[@]}" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Separate process groups let cleanup stop each server and its worker processes.
set -m
printf 'Starting Q-Atlas. Ctrl+C stops both servers.\n'
printf 'Frontend: http://127.0.0.1:5173/compiler\nBackend docs: http://127.0.0.1:8000/docs\n'
(
    cd "$PROJECT_ROOT/backend"
    if [[ -n "$qatlas_prompt_token" ]]; then
        export QATLAS_QUANTUM_KEY="$qatlas_prompt_token"
    fi
    if [[ -n "$qatlas_prompt_instance" ]]; then
        export QATLAS_IBM_INSTANCE="$qatlas_prompt_instance"
    fi
    exec .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) </dev/null &
server_pids+=("$!")
(
    cd "$PROJECT_ROOT/frontend"
    unset QATLAS_QUANTUM_KEY QATLAS_IBM_INSTANCE qatlas_prompt_token qatlas_prompt_instance
    exec env -u QUANTUM-KEY npm run dev -- --clearScreen false
) </dev/null &
server_pids+=("$!")

status=0
wait -n "${server_pids[@]}" || status=$?
printf '\nA server stopped; shutting down the development servers.\n'
exit "$status"
