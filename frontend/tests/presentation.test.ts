import assert from 'node:assert/strict';
import { test } from 'node:test';
import { duration } from '../src/lib/presentation/format.ts';
import { largerWorkload } from '../src/lib/presentation/workloads.ts';
import { hardwareTask } from '../src/lib/hardware/requests.ts';

test('short measured times remain visible with explicit units and missing timers stay missing', () => {
  assert.equal(duration(null), 'Not measured');
  assert.equal(duration(0), '0 ms');
  assert.equal(duration(0.0000005), '0.5 ns');
  assert.equal(duration(0.043631), '43.631 µs');
  assert.equal(duration(1449.293785), '1.449 s');
});
test('larger workload has 16 decisions and 120 distinct weighted edges; hardware bounds remain enforced', () => {
  const problem = largerWorkload();
  assert.equal(problem.kind, 'graph');
  if (problem.kind !== 'graph') return;
  assert.equal(problem.num_vertices, 16);
  assert.equal(problem.edges.length, 120);
  assert.equal(new Set(problem.edges.map((e) => `${e.i},${e.j}`)).size, 120);
  assert.ok(problem.edges.every((e) => e.i < e.j && e.coefficient > 0));
  assert.throws(() => hardwareTask('optimization', { problem }, 128, 3, 4, 1), /at most 8/);
});
