import assert from 'node:assert/strict';
import { test } from 'node:test';
import { graphs, getExampleRun } from '../src/lib/data/fixtures.ts';
import { parseBenchmark } from '../src/lib/api/client.ts';

for (const graph of graphs) {
  test(`${graph.name}: QUBO matches the displayed graph and reference assignment`, () => {
    assert.equal(graph.qubo.num_variables, graph.nodes.length);
    assert.equal(graph.qubo.linear.length, graph.nodes.length);
    assert.equal(graph.qubo.sense, 'minimize');
    const pairs = new Set<string>();
    for (const { i, j, coefficient } of graph.qubo.quadratic) {
      assert.ok(i >= 0 && i < j && j < graph.nodes.length);
      assert.ok(Number.isFinite(coefficient));
      assert.ok(!pairs.has(`${i},${j}`));
      pairs.add(`${i},${j}`);
    }
    assert.equal(pairs.size, graph.edges.length);
    for (const [i, j] of graph.edges) assert.ok(pairs.has(`${Math.min(i, j)},${Math.max(i, j)}`));
    const cut = graph.edges.filter(([i, j]) => graph.assignment[i] !== graph.assignment[j]).length;
    const cost =
      graph.qubo.constant +
      graph.qubo.linear.reduce((sum, a, i) => sum + a * graph.assignment[i], 0) +
      graph.qubo.quadratic.reduce(
        (sum, term) => sum + term.coefficient * graph.assignment[term.i] * graph.assignment[term.j],
        0
      );
    assert.equal(cost, -cut);
    assert.equal(cut, graph.optimumCut);
  });

  test(`${graph.name}: result and histogram use a consistent, explicitly labeled fixture`, () => {
    const run = getExampleRun(graph.id);
    assert.equal(parseBenchmark(run.benchmark).metadata.ui_fixture, true);
    assert.equal(run.benchmark.metadata.timing_scope, 'illustrative_fixture');
    assert.equal(run.benchmark.classical?.objective, -graph.optimumCut);
    assert.equal(
      run.histogram.reduce((sum, bin) => sum + bin.count, 0),
      run.fixtureConfig.shots
    );
    assert.equal(run.fixtureConfig.shots, run.benchmark.metrics.shots);
    assert.equal(run.expected.length, run.bestSampled.length);
    assert.equal(run.expected.length * 2, run.benchmark.metrics.optimizer_evaluations);
    const histogramMean =
      -run.histogram.reduce((sum, bin) => sum + bin.cut * bin.count, 0) / run.fixtureConfig.shots;
    assert.equal(run.expected.at(-1), histogramMean);
    const possibleCuts: Record<string, number[]> = {
      prism: [0, 3, 4, 5, 6, 7],
      cube: [0, 3, 4, 5, 6, 7, 8, 9, 12],
      cycle: [0, 2, 4]
    };
    for (const bin of run.histogram) assert.ok(possibleCuts[graph.id].includes(bin.cut));
    for (const cost of run.bestSampled) assert.ok(possibleCuts[graph.id].includes(-cost));
  });
}

test('loading a fixture returns an independent copy', () => {
  const first = getExampleRun('prism');
  first.histogram[0].count = 0;
  first.benchmark.metadata.ui_fixture = false;
  const second = getExampleRun('prism');
  assert.equal(second.histogram[0].count, 316);
  assert.equal(second.benchmark.metadata.ui_fixture, true);
});

test('an unknown fixture fails explicitly', () => {
  assert.throws(() => getExampleRun('unknown'), /No UI example/);
});
