import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { curvePoints } from '../src/lib/search/live.ts';
import { intervalLabel, samplingInterval, wilson95 } from '../src/lib/search/uncertainty.ts';
import { summarizeTrials, trialCurve } from '../src/lib/search/trials.ts';
import type { SearchResult } from '../src/types/index.ts';

const bundle = JSON.parse(
  readFileSync(new URL('../src/lib/search/previously-measured.json', import.meta.url), 'utf8')
);
const result = (): SearchResult => structuredClone(bundle.curve[0]);
const close = (actual: number, expected: number) => assert.ok(Math.abs(actual - expected) < 1e-10);

test('Wilson reference values and symmetric interval', () => {
  const interval = wilson95(5, 10);
  close(interval[0], 0.236593090512564);
  close(interval[1], 0.763406909487436);
  const rare = wilson95(1, 10);
  close(rare[0], 0.017876213095073);
  close(rare[1], 0.404150026795238);
});

test('zero and all successful shots retain nonzero uncertainty', () => {
  assert.equal(wilson95(0, 10)[0], 0);
  close(wilson95(0, 10)[1], 0.277532799862889);
  close(wilson95(10, 10)[0], 1 - 0.277532799862889);
  assert.equal(wilson95(10, 10)[1], 1);
  assert.ok(wilson95(0, 1)[1] > 0.79);
});

test('intervals contain estimates, stay bounded, and narrow at fixed probability', () => {
  for (let n = 1; n <= 100; n++)
    for (let k = 0; k <= n; k++) {
      const [lo, hi] = wilson95(k, n);
      assert.ok(0 <= lo && lo <= k / n && k / n <= hi && hi <= 1);
      const mirrored = wilson95(n - k, n);
      close(lo, 1 - mirrored[1]);
    }
  assert.ok(
    wilson95(500, 1000)[1] - wilson95(500, 1000)[0] < wilson95(5, 10)[1] - wilson95(5, 10)[0]
  );
});

test('invalid counts are rejected instead of fabricating intervals', () => {
  for (const [k, n] of [
    [0, 0],
    [-1, 10],
    [11, 10],
    [1.5, 10],
    [1, 2.5],
    [NaN, 10],
    [1, Infinity],
    [1, 2 ** 53]
  ]) {
    assert.throws(() => wilson95(k, n), /integer/);
  }
});

test('missing counts are unavailable; inconsistent probability is rejected', () => {
  const run = result();
  run.metrics.successful_shots = null;
  assert.equal(samplingInterval(run), null);
  assert.equal(intervalLabel(null), 'Not available');
  assert.equal(curvePoints([run])[0].confidenceInterval, undefined);
  const inconsistent = result();
  inconsistent.metrics.success_probability = 0.999;
  assert.throws(() => samplingInterval(inconsistent), /disagrees/);
});

test('recorded curve derives intervals without changing raw results', () => {
  const runs: SearchResult[] = structuredClone(bundle.curve);
  const before = structuredClone(runs);
  for (const [index, point] of curvePoints(runs).entries()) {
    assert.deepEqual(
      point.confidenceInterval,
      wilson95(runs[index].metrics.successful_shots!, runs[index].metrics.shots!)
    );
  }
  assert.deepEqual(runs, before);
  assert.equal(intervalLabel([0.1, 0.9]), '10.00%–90.00%');
});

test('trial mean keeps descriptive range and never receives a pooled confidence interval', () => {
  const points = trialCurve(summarizeTrials(bundle.trials));
  assert.ok(points[0].observedRange);
  assert.equal(points[0].confidenceInterval, undefined);
});
