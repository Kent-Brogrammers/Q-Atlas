import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, createApiClient } from '../src/api/client.ts';
import { graphs } from '../src/lib/data/fixtures.ts';
import {
  buildRequest,
  buildMeasuredExport,
  defaultSettings,
  measureOptimization,
  milliseconds
} from '../src/lib/optimization/live.ts';
import type { OptimizationRequest, OptimizationResult } from '../src/types/index.ts';

const graph = graphs[2];

function response(request: OptimizationRequest, selected = graph): OptimizationResult {
  // Synthetic transport fixture confined to tests.
  const config = request.config ?? {};
  const timing = {
    includes_queue: false,
    includes_transpilation: false,
    includes_optimizer: false,
    includes_sampling: false
  };
  const bits = selected.assignment.join('');
  const metrics = {
    num_qubits: selected.nodes.length,
    shots: config.shots,
    circuit_depth: 0,
    optimizer_evaluations: 0,
    optimality_gap: 0,
    approximation_ratio: null
  };
  return {
    experiment: 'optimization',
    status: 'completed',
    problem_id: 'synthetic-transport-fixture',
    backend: 'aer_simulator',
    classical: {
      algorithm: 'brute_force',
      objective: -selected.optimumCut,
      best_bitstring: bits,
      elapsed_ms: 0,
      timing
    },
    quantum: {
      algorithm: 'qaoa',
      objective: -selected.optimumCut,
      best_bitstring: bits,
      elapsed_ms: 0,
      timing,
      metrics
    },
    metrics,
    metadata: {
      config,
      seed: config.seed ?? 42,
      timing_scope: 'end_to_end',
      simulation_method: 'statevector',
      simulated: true,
      qubo: { ...structuredClone(selected.qubo), original_sense: 'maximize' }
    }
  };
}

for (const selected of graphs) {
  test(`${selected.name} sends graph edges and the selected solver settings`, () => {
    const settings = {
      ...defaultSettings(),
      seed: 0,
      layers: 8,
      shots: 1,
      maxIterations: 1,
      timeout: 0.01
    };
    const original = structuredClone(selected);
    const request = buildRequest(selected, settings);
    assert.deepEqual(request.problem, {
      kind: 'graph',
      num_vertices: selected.nodes.length,
      edges: selected.edges.map(([i, j]) => ({ i, j, coefficient: 1 }))
    });
    assert.deepEqual(request.config, {
      backend: 'aer_simulator',
      optimizer: 'COBYLA',
      p: 8,
      shots: 1,
      seed: 0,
      max_iterations: 1,
      timeout_seconds: 0.01
    });
    assert.deepEqual(selected, original);
  });
}

for (const [key, value] of [
  ['layers', undefined],
  ['layers', 0],
  ['layers', 9],
  ['layers', 1.5],
  ['shots', 0],
  ['shots', 100001],
  ['shots', Number.NaN],
  ['seed', undefined],
  ['seed', -1],
  ['seed', 2 ** 32],
  ['seed', 1.5],
  ['maxIterations', 0],
  ['maxIterations', 1001],
  ['timeout', undefined],
  ['timeout', 0],
  ['timeout', 61],
  ['timeout', Infinity]
] as const) {
  test(`invalid ${key}=${String(value)} is rejected before transport`, async () => {
    let called = false;
    await assert.rejects(
      measureOptimization(
        graph,
        { ...defaultSettings(), [key]: value },
        async (request) => {
          called = true;
          return response(request);
        },
        new AbortController().signal
      )
    );
    assert.equal(called, false);
  });
}

test('typed transport reaches the optimization API and preserves measured zero values', async () => {
  const settings = { ...defaultSettings(), seed: 0 };
  const request = buildRequest(graph, settings);
  const expected = response(request);
  const client = createApiClient({
    baseUrl: 'http://localhost:8000/api',
    fetcher: async (url, init) => {
      assert.equal(url, 'http://localhost:8000/api/optimization/run');
      assert.deepEqual(JSON.parse(String(init?.body)), request);
      assert.ok(init?.signal instanceof AbortSignal);
      return Response.json(expected);
    }
  });
  const completed = await measureOptimization(
    graph,
    settings,
    client.optimization,
    new AbortController().signal
  );
  assert.deepEqual(completed, { request, result: expected });
  assert.equal(completed.result.quantum?.best_bitstring, '0101');
  assert.equal(completed.result.metrics.optimality_gap, 0);
  assert.equal(milliseconds(completed.result.quantum?.elapsed_ms), '0.000 ms');
  assert.equal(milliseconds(null), 'Not measured');
});

test('nullable solver and metric values stay unavailable', async () => {
  const request = buildRequest(graph, defaultSettings());
  const expected = response(request);
  expected.classical = null;
  expected.quantum = null;
  expected.metrics = { shots: null, circuit_depth: null, optimality_gap: null };
  const completed = await measureOptimization(
    graph,
    defaultSettings(),
    async () => expected,
    new AbortController().signal
  );
  assert.deepEqual(completed.result.metrics, expected.metrics);
  assert.equal(completed.result.quantum, null);
});

test('a nullable classical objective and assignment remain unavailable', async () => {
  const expected = response(buildRequest(graph, defaultSettings()));
  expected.classical!.objective = null;
  expected.classical!.best_bitstring = null;
  const completed = await measureOptimization(
    graph,
    defaultSettings(),
    async () => expected,
    new AbortController().signal
  );
  assert.equal(completed.result.classical?.objective, null);
  assert.equal(completed.result.classical?.best_bitstring, null);
});

test('a settings edit during transport preserves the submitted request snapshot', async () => {
  const settings = defaultSettings();
  const completed = await measureOptimization(
    graph,
    settings,
    async (request) => {
      settings.seed = 99;
      return response(request);
    },
    new AbortController().signal
  );
  assert.equal(completed.request.config?.seed, 42);
  assert.equal(completed.result.metadata.seed, 42);
});

for (const status of [422, 503, 504]) {
  test(`HTTP ${status} remains an error with no example fallback`, async () => {
    const client = createApiClient({
      fetcher: async () =>
        Response.json(
          { status: 'error', error: { code: 'HTTP_ERROR', message: 'Synthetic failure' } },
          { status }
        )
    });
    await assert.rejects(
      measureOptimization(
        graph,
        defaultSettings(),
        client.optimization,
        new AbortController().signal
      ),
      (error: unknown) => error instanceof ApiError && error.status === status
    );
  });
}

test('cancellation rejects a late response even when transport ignores the signal', async () => {
  const controller = new AbortController();
  let release!: (value: OptimizationResult) => void;
  const request = buildRequest(graph, defaultSettings());
  const pending = measureOptimization(
    graph,
    defaultSettings(),
    async () =>
      new Promise((resolve) => {
        release = resolve;
      }),
    controller.signal
  );
  controller.abort();
  release(response(request));
  await assert.rejects(pending, { name: 'AbortError' });
});

test('an already cancelled comparison sends no request', async () => {
  let called = false;
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    measureOptimization(
      graph,
      defaultSettings(),
      async (request) => {
        called = true;
        return response(request);
      },
      controller.signal
    ),
    { name: 'AbortError' }
  );
  assert.equal(called, false);
});

for (const corrupt of [
  (value: OptimizationResult) => {
    value.metadata.config.seed = 9;
  },
  (value: OptimizationResult) => {
    value.metadata.seed = 9;
  },
  (value: OptimizationResult) => {
    value.metadata.qubo.linear[0] = 99;
  },
  (value: OptimizationResult) => {
    value.metadata.qubo.quadratic = [];
  },
  (value: OptimizationResult) => {
    value.quantum!.best_bitstring = '1010x';
  },
  (value: OptimizationResult) => {
    value.quantum!.objective = Infinity;
  }
]) {
  test('mismatched or invalid result data is rejected before display', async () => {
    const expected = response(buildRequest(graph, defaultSettings()));
    corrupt(expected);
    await assert.rejects(
      measureOptimization(
        graph,
        defaultSettings(),
        async () => expected,
        new AbortController().signal
      )
    );
  });
}

test('export retains the actual request, timing flags, and all raw result fields', async () => {
  const completed = await measureOptimization(
    graph,
    defaultSettings(),
    async (request) => response(request),
    new AbortController().signal
  );
  const exported = buildMeasuredExport(completed);
  assert.equal(exported.source, 'live_local_simulator');
  assert.deepEqual(exported.request, completed.request);
  assert.deepEqual(exported.result, completed.result);
  exported.result.metadata.config.seed = 9;
  assert.equal(completed.result.metadata.config.seed, 42);
  assert.equal('example_chart_data' in exported, false);
});
