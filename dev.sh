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

# The backend loads optional .env quantum settings itself. Missing credentials never prompt.

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
    # Local simulator execution is enabled for the development app; operators can set 0.
    export QATLAS_ENABLE_COMPILER_AER="${QATLAS_ENABLE_COMPILER_AER:-1}"
    exec .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) </dev/null &
server_pids+=("$!")
(
    cd "$PROJECT_ROOT/frontend"
    unset QATLAS_QUANTUM_KEY QATLAS_IBM_INSTANCE
    exec env -u QUANTUM-KEY -u QUANTUM-CDN npm run dev -- --clearScreen false
) </dev/null &
server_pids+=("$!")

status=0
wait -n "${server_pids[@]}" || status=$?
printf '\nA server stopped; shutting down the development servers.\n'
exit "$status"
