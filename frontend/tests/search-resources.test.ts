import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { gateResources } from '../src/lib/search/resources.ts';
import type { SearchResult } from '../src/types/index.ts';

const bundle = JSON.parse(
  readFileSync(new URL('../src/lib/search/previously-measured.json', import.meta.url), 'utf8')
);
const result = (): SearchResult => structuredClone(bundle.curve[0]);

test('legacy recordings leave gate resources unavailable', () => {
  assert.equal(gateResources(result()), null);
});

test('gate display totals a sorted histogram without multiplying by shots', () => {
  const run = result();
  run.metrics.circuit_gate_counts = { h: 3, ccx: 2 };
  const before = structuredClone(run);
  assert.deepEqual(gateResources(run), { total: 5, breakdown: 'ccx: 2 · h: 3' });
  assert.deepEqual(run, before);
  run.metrics.shots = 10000;
  assert.equal(gateResources(run)?.total, 5);
});

test('zero gate circuit is distinct from unavailable evidence', () => {
  const run = result();
  run.metrics.circuit_gate_counts = {};
  assert.deepEqual(gateResources(run), { total: 0, breakdown: 'No gates' });
});

test('invalid counts never become displayed resources', () => {
  const cases: Record<string, number>[] = [
    { h: -1 },
    { h: 0 },
    { h: 1.5 },
    { h: NaN },
    { '': 1 },
    { h: Number.MAX_SAFE_INTEGER, x: 1 }
  ];
  for (const counts of cases) {
    const run = result();
    run.metrics.circuit_gate_counts = counts;
    assert.throws(() => gateResources(run), /invalid|safe integer/);
  }
});
