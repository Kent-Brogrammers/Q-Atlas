import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, createApiClient, parseBenchmark } from '../src/lib/api/client.ts';
import { getExampleRun } from '../src/lib/data/fixtures.ts';

test('the documented benchmark shape preserves zero, null, and experiment metadata', () => {
  const fixture = getExampleRun('cycle').benchmark;
  fixture.classical = { algorithm: 'reference', elapsed_ms: 0, objective: 0 };
  fixture.quantum = null;
  fixture.metrics['custom_metric'] = null;
  assert.deepEqual(parseBenchmark(fixture), fixture);
});

test('nullable solver measurements remain not-applicable instead of becoming zero', () => {
  const fixture = getExampleRun('prism').benchmark;
  fixture.quantum = { algorithm: 'qaoa', objective: null, elapsed_ms: null };
  assert.deepEqual(parseBenchmark(fixture).quantum, fixture.quantum);
});

for (const [name, payload] of [
  ['missing fields', {}],
  ['wrong experiment', { ...getExampleRun('prism').benchmark, experiment: 'invented' }],
  [
    'negative elapsed time',
    {
      ...getExampleRun('prism').benchmark,
      classical: { algorithm: 'exact', elapsed_ms: -1, objective: -7 }
    }
  ],
  [
    'non-finite objective',
    {
      ...getExampleRun('prism').benchmark,
      quantum: { algorithm: 'qaoa', elapsed_ms: 1, objective: Infinity }
    }
  ],
  ['invalid metrics', { ...getExampleRun('prism').benchmark, metrics: [] }]
] as const) {
  test(`rejects a malformed result: ${name}`, () => {
    assert.throws(() => parseBenchmark(payload), ApiError);
  });
}

test('the client posts caller-supplied JSON to the documented endpoint', async () => {
  const fixture = getExampleRun('prism').benchmark;
  const payload = { qubo: { num_variables: 0 }, note: 'request envelope remains a team decision' };
  const fetcher: typeof fetch = async (url, init) => {
    assert.equal(url, 'http://localhost:8000/api/optimization/run');
    assert.equal(init?.method, 'POST');
    assert.equal(new Headers(init?.headers).get('Content-Type'), 'application/json');
    assert.deepEqual(JSON.parse(String(init?.body)), payload);
    assert.ok(init?.signal instanceof AbortSignal);
    return Response.json(fixture);
  };
  const result = await createApiClient({
    baseUrl: 'http://localhost:8000/',
    fetcher
  }).postBenchmark('/api/optimization/run', payload);
  assert.deepEqual(result, fixture);
});

test('HTTP failures retain the status and never fall back to example data', async () => {
  const fetcher: typeof fetch = async () =>
    new Response('internal backend details', { status: 503 });
  await assert.rejects(
    createApiClient({ fetcher }).postBenchmark('/api/optimization/run', {}),
    (error: unknown) =>
      error instanceof ApiError &&
      error.status === 503 &&
      !error.message.includes('internal backend details')
  );
});

test('connection failure is reported as a client error', async () => {
  const fetcher: typeof fetch = async () => {
    throw new TypeError('Failed to fetch');
  };
  await assert.rejects(createApiClient({ fetcher }).postBenchmark('/api/search/run', {}), ApiError);
});

test('invalid JSON does not become a successful benchmark', async () => {
  const fetcher: typeof fetch = async () => new Response('invalid json');
  await assert.rejects(
    createApiClient({ fetcher }).postBenchmark('/api/materials/run', {}),
    ApiError
  );
});

test('caller cancellation reaches the request and produces an explicit error', async () => {
  const controller = new AbortController();
  controller.abort();
  const fetcher: typeof fetch = async (_, init) => {
    assert.equal(init?.signal?.aborted, true);
    throw new DOMException('Request aborted', 'AbortError');
  };
  await assert.rejects(
    createApiClient({ fetcher }).postBenchmark('/api/optimization/run', {}, controller.signal),
    /cancelled or timed out/
  );
});
