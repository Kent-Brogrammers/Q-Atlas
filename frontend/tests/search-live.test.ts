import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, createApiClient } from '../src/api/client.ts';
import {
  buildRequest,
  curvePoints,
  defaultSettings,
  measureSweep,
  milliseconds,
  percentage
} from '../src/lib/search/live.ts';
import type { SearchRequest, SearchResult } from '../src/types/index.ts';

// Synthetic wire fixtures for tests only; never imported by the live application.
function fixture(request: SearchRequest): SearchResult {
  return {
    experiment: 'search',
    status: 'completed',
    problem_id: 'test-only',
    backend: 'aer_simulator',
    classical: null,
    quantum: null,
    metrics: { success_probability: 0, theoretical_success_probability: 0.125 },
    metadata: {
      seed: 42,
      timing_scope: 'end_to_end',
      simulated: true,
      simulation_method: 'statevector',
      parameters: request,
      oracle_assumptions: 'Test fixture only.'
    }
  };
}

test('search request preserves leading zeros, zero settings, and multiple targets', () => {
  const settings = {
    ...defaultSettings(),
    targets: '001, 110\n010',
    seed: 0,
    automatic: false,
    iterations: 0
  };
  const before = structuredClone(settings);
  const request = buildRequest(settings);
  assert.deepEqual(request.marked_states, ['001', '110', '010']);
  assert.equal(request.config?.seed, 0);
  assert.equal(request.iterations, 0);
  assert.deepEqual(settings, before);
});

test('automatic selection does not require a manual iteration input', () => {
  assert.equal(buildRequest({ ...defaultSettings(), iterations: undefined }).iterations, null);
});

test('invalid search settings are rejected before transport', () => {
  for (const patch of [
    { targets: '' },
    { targets: '001,001' },
    { targets: '01' },
    { targets: 'abc' },
    { numQubits: 7 },
    { numQubits: undefined },
    { shots: 0 },
    { shots: 10001 },
    { shots: 1.5 },
    { seed: -1 },
    { seed: 2 ** 32 },
    { timeout: 0 },
    { timeout: NaN },
    { timeout: 61 },
    { automatic: false, iterations: undefined },
    { automatic: false, iterations: 33 }
  ])
    assert.throws(() => buildRequest({ ...defaultSettings(), ...patch }));
});

test('curve requests are sequential, bounded, and retain the same instance/settings', async () => {
  const requests: SearchRequest[] = [];
  const progress: number[][] = [];
  let active = 0,
    maxActive = 0;
  const signal = new AbortController().signal;
  const results = await measureSweep(
    defaultSettings(),
    3,
    async (request, receivedSignal) => {
      assert.equal(receivedSignal, signal);
      active++;
      maxActive = Math.max(active, maxActive);
      await Promise.resolve();
      requests.push(request);
      active--;
      return fixture(request);
    },
    signal,
    (done, total) => progress.push([done, total])
  );
  assert.equal(maxActive, 1);
  assert.deepEqual(
    requests.map((request) => request.iterations),
    [0, 1, 2, 3]
  );
  assert.deepEqual(progress, [
    [1, 4],
    [2, 4],
    [3, 4],
    [4, 4]
  ]);
  assert.equal(results.length, 4);
  for (const request of requests) {
    assert.deepEqual(request.marked_states, ['001']);
    assert.equal(request.config?.shots, 1024);
    assert.equal(request.config?.seed, 42);
  }
});

test('invalid sweep limits never send requests', async () => {
  for (const max of [-1, 13, 1.5, undefined]) {
    await assert.rejects(
      measureSweep(
        defaultSettings(),
        max,
        async () => {
          assert.fail('must reject before transport');
        },
        new AbortController().signal
      )
    );
  }
});

test('sweep ignores blank manual iterations and allows a zero-only curve', async () => {
  const results = await measureSweep(
    { ...defaultSettings(), automatic: false, iterations: undefined },
    0,
    async (request) => fixture(request),
    new AbortController().signal
  );
  assert.equal(results.length, 1);
  assert.equal(results[0].metadata.parameters.iterations, 0);
});

test('a failed curve stops immediately and never returns partial success', async () => {
  let calls = 0;
  await assert.rejects(
    measureSweep(
      defaultSettings(),
      4,
      async (request) => {
        if (++calls === 2) throw new Error('backend unavailable');
        return fixture(request);
      },
      new AbortController().signal
    ),
    /backend unavailable/
  );
  assert.equal(calls, 2);
});

test('pre-cancelled sweeps send no requests', async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    measureSweep(
      defaultSettings(),
      2,
      async () => {
        assert.fail('cancelled sweep must not start');
      },
      controller.signal
    ),
    { name: 'AbortError' }
  );
});

test('cancelling in-flight work prevents later requests and publication of stale results', async () => {
  const controller = new AbortController();
  let calls = 0;
  await assert.rejects(
    measureSweep(
      defaultSettings(),
      3,
      async (request) => {
        calls++;
        controller.abort();
        return fixture(request);
      },
      controller.signal
    ),
    { name: 'AbortError' }
  );
  assert.equal(calls, 1);
});

test('curve rejects mismatched backend iteration metadata', async () => {
  await assert.rejects(
    measureSweep(
      defaultSettings(),
      1,
      async (request) => fixture({ ...request, iterations: 9 }),
      new AbortController().signal
    ),
    /different curve iteration/
  );
});

test('display preserves measured zero and missing probabilities separately', () => {
  const result = fixture({ ...buildRequest(defaultSettings()), iterations: 0 });
  result.metrics.theoretical_success_probability = null;
  assert.deepEqual(curvePoints([result]), [{ iteration: 0, measured: 0, theoretical: null }]);
  assert.equal(percentage(0), '0.0%');
  assert.equal(percentage(null), 'Not available');
  assert.equal(milliseconds(0), '0.000 ms');
  assert.equal(milliseconds(undefined), 'Not measured');
  assert.deepEqual(curvePoints([]), []);
});

test('invalid backend probabilities or missing effective iterations are not plotted', () => {
  for (const value of [NaN, Infinity, -0.1, 1.1]) {
    const result = fixture({ ...buildRequest(defaultSettings()), iterations: 0 });
    result.metrics.success_probability = value;
    assert.throws(() => curvePoints([result]), /invalid probability/);
  }
  assert.throws(
    () => curvePoints([fixture(buildRequest(defaultSettings()))]),
    /effective iteration/
  );
});

test('typed search transport returns backend results without example fallback', async () => {
  const request = { ...buildRequest(defaultSettings()), iterations: 2 };
  const result = fixture(request);
  result.metrics.shots = 1024;
  result.metrics.successful_shots = 0;
  result.metrics.classical_observed_queries = 2;
  result.metrics.quantum_oracle_queries = 2;
  result.metrics.quantum_total_oracle_queries = 2048;
  const fetcher: typeof fetch = async (url, init) => {
    assert.equal(url, 'http://localhost:8000/api/search/run');
    assert.equal(init?.method, 'POST');
    assert.deepEqual(JSON.parse(String(init?.body)), request);
    return Response.json(result);
  };
  assert.deepEqual(
    await createApiClient({ baseUrl: 'http://localhost:8000/api', fetcher }).search(request),
    result
  );
});

test('search dependency, validation, timeout and network errors remain failures', async () => {
  for (const status of [422, 503, 504]) {
    const fetcher: typeof fetch = async () =>
      Response.json(
        {
          status: 'error',
          error: {
            code: 'HTTP_ERROR',
            message: 'Search failed.',
            diagnostics: []
          }
        },
        { status }
      );
    await assert.rejects(
      createApiClient({ fetcher }).search(buildRequest(defaultSettings())),
      (error: unknown) => error instanceof ApiError && error.status === status
    );
  }
  await assert.rejects(
    createApiClient({
      fetcher: async () => {
        throw new TypeError('offline');
      }
    }).search(buildRequest(defaultSettings())),
    /could not be reached/
  );
});
