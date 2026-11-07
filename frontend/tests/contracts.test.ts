import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, createApiClient } from '../src/lib/api/client.ts';
import type { ErrorResponse, OptimizationRequest, OptimizationResult } from '../src/types/index.ts';
import { graphs } from '../src/lib/data/fixtures.ts';

const request: OptimizationRequest = {
  problem: { kind: 'qubo', qubo: graphs[0].qubo },
  config: { p: 2, shots: 1024, seed: 0, optimizer: 'COBYLA' }
};
const unavailable: ErrorResponse = {
  status: 'error',
  error: {
    code: 'NOT_IMPLEMENTED',
    message: 'Optimization benchmark is not implemented.',
    diagnostics: []
  }
};

test('the shared optimization request and generated response types preserve zero and null', async () => {
  // Transport fixture only, never shown as a measured result in the application.
  const result: OptimizationResult = {
    status: 'completed',
    experiment: 'optimization',
    problem_id: 'contract-test',
    backend: 'aer_simulator',
    classical: null,
    quantum: null,
    metrics: { shots: null },
    metadata: {
      seed: 0,
      timing_scope: 'end_to_end',
      simulation_method: 'statevector',
      qubo: graphs[0].qubo,
      config: request.config ?? {}
    }
  };
  const fetcher: typeof fetch = async (url, init) => {
    assert.equal(url, 'http://localhost:8000/api/optimization/run');
    assert.equal(init?.method, 'POST');
    assert.equal(new Headers(init?.headers).get('Content-Type'), 'application/json');
    assert.deepEqual(JSON.parse(String(init?.body)), request);
    assert.ok(init?.signal instanceof AbortSignal);
    return Response.json(result);
  };
  assert.deepEqual(
    await createApiClient({ baseUrl: 'http://localhost:8000/api/', fetcher }).optimization(request),
    result
  );
});

test('health uses GET and keeps experiment readiness distinct from API readiness', async () => {
  const health = {
    status: 'ok',
    service: 'q-atlas',
    backend: 'aer_simulator',
    experiments_ready: false
  };
  const fetcher: typeof fetch = async (url, init) => {
    assert.equal(url, 'http://localhost:8000/api/health');
    assert.equal(init?.method, 'GET');
    assert.equal(init?.body, undefined);
    return Response.json(health);
  };
  const client = createApiClient({ baseUrl: 'http://localhost:8000/api', fetcher });
  assert.equal((await client.health()).experiments_ready, false);
});

test('analysis forwards source as JSON to the shared compiler endpoint', async () => {
  const source = { source: '@qatlas.objective(num_bits=1)\ndef objective(x):\n    return x[0]' };
  const result = { status: 'rejected', diagnostics: [], qubo: null, circuit: null };
  const fetcher: typeof fetch = async (url, init) => {
    assert.equal(url, 'http://localhost:8000/api/compiler/analyze');
    assert.deepEqual(JSON.parse(String(init?.body)), source);
    return Response.json(result);
  };
  assert.deepEqual(
    await createApiClient({ baseUrl: 'http://localhost:8000/api', fetcher }).analyze(source),
    result
  );
});

for (const [endpoint, payload] of [
  ['/api/compiler/benchmark', { source: 'def objective(x): return x[0]' }],
  ['/api/search/run', { num_qubits: 3, marked_states: ['100'] }],
  ['/api/materials/run', {}]
] as const) {
  test(`${endpoint}: typed request reaches the shared endpoint and preserves HTTP 501`, async () => {
    const fetcher: typeof fetch = async (url, init) => {
      assert.equal(url, `http://localhost:8000${endpoint}`);
      assert.deepEqual(JSON.parse(String(init?.body)), payload);
      return Response.json(unavailable, { status: 501 });
    };
    const client = createApiClient({ baseUrl: 'http://localhost:8000/api', fetcher });
    // Narrow the discriminated endpoint/payload pair for TypeScript.
    const action =
      endpoint === '/api/compiler/benchmark'
        ? client.compilerBenchmark(payload)
        : endpoint === '/api/search/run'
          ? client.search({ ...payload, marked_states: [...payload.marked_states] })
          : client.materials(payload);
    await assert.rejects(
      action,
      (error: unknown) =>
        error instanceof ApiError &&
        error.status === 501 &&
        error.body.error.code === 'NOT_IMPLEMENTED'
    );
  });
}

for (const [status, code] of [
  [501, 'NOT_IMPLEMENTED'],
  [422, 'VALIDATION_ERROR']
] as const) {
  test(`HTTP ${status}: preserves the canonical structured error without example fallback`, async () => {
    const body: ErrorResponse = {
      status: 'error',
      error: { code, message: 'Request rejected.', diagnostics: [] }
    };
    const fetcher: typeof fetch = async () => Response.json(body, { status });
    await assert.rejects(
      createApiClient({ fetcher }).optimization(request),
      (error: unknown) =>
        error instanceof ApiError && error.status === status && error.body.error.code === code
    );
  });
}

test('unstructured HTTP errors do not expose server response text', async () => {
  const fetcher: typeof fetch = async () =>
    new Response('internal backend details', { status: 503 });
  await assert.rejects(
    createApiClient({ fetcher }).optimization(request),
    (error: unknown) =>
      error instanceof ApiError &&
      error.status === 503 &&
      !error.message.includes('internal backend details')
  );
});

test('connection failure stays a failure', async () => {
  const fetcher: typeof fetch = async () => {
    throw new TypeError('Failed to fetch');
  };
  await assert.rejects(createApiClient({ fetcher }).optimization(request), /could not be reached/);
});

test('invalid JSON does not become a successful benchmark', async () => {
  const fetcher: typeof fetch = async () => new Response('invalid json');
  await assert.rejects(createApiClient({ fetcher }).optimization(request), /invalid JSON/);
});

test('caller cancellation reaches the request and produces an explicit error', async () => {
  const controller = new AbortController();
  controller.abort();
  const fetcher: typeof fetch = async (_, init) => {
    assert.equal(init?.signal?.aborted, true);
    throw new DOMException('Request aborted', 'AbortError');
  };
  await assert.rejects(
    createApiClient({ fetcher }).optimization(request, controller.signal),
    /cancelled or timed out/
  );
});
