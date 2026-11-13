import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  axes,
  cycleProblem,
  integers,
  measurements,
  planStudy,
  summarize
} from '../src/lib/studies/model.ts';
import { runStudy } from '../src/lib/studies/runner.ts';
import { loadRecordedDemo } from '../src/lib/search/recorded.ts';
import { buildRequest, defaultSettings } from '../src/lib/neutrinos/live.ts';
import type { MaterialsRequest, OptimizationRequest, SearchRequest } from '../src/types/index.ts';

const search: SearchRequest = {
  num_qubits: 3,
  marked_states: ['001'],
  config: { shots: 1024, seed: 42, timeout_seconds: 30 }
};
const measured = () => structuredClone(loadRecordedDemo('curve').results[2]);

test('plans preserve fixed inputs and snapshot every value/seed without mutating the base request', () => {
  const before = structuredClone(search);
  const plan = planStudy('search', search, 'shots', '256, 1024', '0, 4294967295');
  assert.equal(plan.points.length, 4);
  assert.equal(plan.totalShots, 2560);
  assert.deepEqual(
    plan.points.map((p) => p.request.config!.seed),
    [0, 4294967295, 0, 4294967295]
  );
  assert.deepEqual(search, before);
  plan.points[0].request.marked_states[0] = '111';
  assert.equal(plan.points[1].request.marked_states[0], '001');
});

test('resource plans reject duplicate, fractional, oversized and unsupported grids before execution', () => {
  for (const value of ['', '1,', '1,1', '-1', '1.2', 'Infinity'])
    assert.throws(() => integers(value, 'Grid', 0, 100));
  assert.throws(() => planStudy('search', search, 'p', '1', '42'), /Unsupported/);
  assert.throws(() => planStudy('search', search, 'shots', '10001', '42'), /10000/);
  assert.throws(
    () => planStudy('search', search, 'iterations', '0,1,2,3,4,5,6,7', '1,2,3,4'),
    /24 requests/
  );
  assert.throws(() => planStudy('search', search, 'shots', '1024', '42', 121), /budget/);
});

test('size studies use explicit controlled families and fair target placement', () => {
  const s = planStudy('search', search, 'size', '2,6', '42');
  assert.deepEqual(
    s.points.map((p) => [p.request.num_qubits, p.request.marked_states, p.request.iterations]),
    [
      [2, ['00'], null],
      [6, ['000000'], null]
    ]
  );
  const base: OptimizationRequest = { problem: cycleProblem(4), config: { p: 2 } };
  const o = planStudy('optimization', base, 'size', '4,8', '42');
  assert.deepEqual(
    o.points.map((p) => p.request.problem),
    [cycleProblem(4), cycleProblem(8)]
  );
  assert.equal((cycleProblem(16) as { edges: unknown[] }).edges.length, 16);
});

test('materials study fixes terminal time and counts both measurement bases; neutrino curves count every point', () => {
  const m: MaterialsRequest = {
    num_spins: 3,
    evolution_time: 1,
    time_samples: 5,
    trotter_steps: 32,
    config: { shots: 512 }
  };
  const p = planStudy('materials', m, 'trotter_steps', '1,32', '42,142');
  assert.equal(p.totalShots, 4096);
  assert.ok(
    p.points.every(
      (point) => point.request.time_samples === 1 && point.request.evolution_time === 1
    )
  );
  const n = buildRequest(defaultSettings());
  assert.equal(planStudy('neutrinos', n, 'shots', '256,1024', '42').totalShots, 21 * 1280);
  assert.throws(() => planStudy('neutrinos', n, 'shots', '100000', '42'), /500,000/);
  assert.equal(Object.keys(axes).length, 5);
});

test('runner is sequential and summary preserves measured zero, counts and raw responses', async () => {
  const plan = planStudy('search', search, 'shots', '256,1024', '42,142');
  let active = 0;
  const report = await runStudy(
    plan,
    async () => {
      assert.equal(active++, 0);
      await Promise.resolve();
      const response = measured();
      response.classical!.elapsed_ms = active - 1; // zero is a real measurement
      active--;
      return response;
    },
    new AbortController().signal
  );
  assert.equal(report.status, 'completed');
  assert.equal(report.records.length, 4);
  assert.equal(report.records[0].response!.metrics.successful_shots, 986);
  const summary = summarize(report);
  assert.equal(summary[0].count, 2);
  assert.deepEqual(summary[0].metrics['Classical reference (ms)'], {
    count: 2,
    median: 0,
    min: 0,
    max: 0
  });
  assert.equal(measurements('search', report.records[0].response!)['Measured success'], 986 / 1024);
});

test('failure retains partial evidence, excludes failed points and schedules no further requests', async () => {
  const plan = planStudy('search', search, 'shots', '256,1024', '42');
  let calls = 0;
  const report = await runStudy(
    plan,
    async () => {
      if (++calls === 2) throw new Error('Backend unavailable');
      return measured();
    },
    new AbortController().signal
  );
  assert.equal(calls, 2);
  assert.equal(report.status, 'incomplete');
  assert.equal(report.records[1].error, 'Backend unavailable');
  assert.equal(report.records[1].response, undefined);
  assert.equal(summarize(report)[1].count, 0);
});

test('cancelled response never becomes a completed measurement and stops scheduling', async () => {
  const controller = new AbortController();
  const plan = planStudy('search', search, 'shots', '256,1024', '42');
  let calls = 0;
  const report = await runStudy(
    plan,
    async () => {
      calls++;
      controller.abort();
      return measured();
    },
    controller.signal
  );
  assert.equal(calls, 1);
  assert.equal(report.records[0].status, 'cancelled');
  assert.equal(report.records[0].response, undefined);
  assert.equal(summarize(report)[0].count, 0);
  const preAborted = await runStudy(
    plan,
    async () => {
      throw new Error('must not execute');
    },
    controller.signal
  );
  assert.equal(preAborted.records.length, 0);
});

test('suite deadline cancels the active request and returns exportable incomplete evidence', async () => {
  const plan = planStudy('search', search, 'shots', '256', '42');
  plan.budgetSeconds = 0.01;
  const report = await runStudy(
    plan,
    async (_request, signal) =>
      new Promise((_, reject) => {
        signal.addEventListener('abort', () => reject(new Error('deadline')), { once: true });
      }),
    new AbortController().signal
  );
  assert.equal(report.status, 'incomplete');
  assert.equal(report.records[0].status, 'cancelled');
});
