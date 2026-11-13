import assert from 'node:assert/strict';
import { test } from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';
import { createLabRunner, preset, type RunState } from '../src/lib/neutrinos/session.ts';
import { buildRequest, curveValues } from '../src/lib/neutrinos/live.ts';
import type { NeutrinoResponse } from '../src/types/index.ts';

test('edits invalidate results, serialize in-flight work and execute only the latest settings', async () => {
  const pending: Array<(r: NeutrinoResponse) => void> = [];
  const states: RunState[] = [];
  const energies: number[] = [];
  const runner = createLabRunner(
    (req) => {
      energies.push(req.experiment.parameters!.energy!);
      return new Promise((resolve) => pending.push(resolve));
    },
    (s) => states.push(s)
  );
  const settings = preset('vacuum');
  runner.update(settings, 0);
  await delay(10);
  assert.equal(states.at(-1)?.status, 'running');
  runner.update({ ...settings, energy: 2 }, 0);
  runner.update({ ...settings, energy: 3 }, 0);
  await delay(10);
  assert.deepEqual(energies, [1]);
  assert.equal(states.at(-1)?.status, 'waiting');
  const result = { axis: 'distance', coordinates: [], results: [] } as NeutrinoResponse;
  pending.shift()!(result);
  await delay(0);
  assert.deepEqual(energies, [1, 3]);
  assert.ok(!states.some((s) => s.status === 'ready'));
  pending.shift()!(result);
  await delay(0);
  const final = states.at(-1);
  assert.equal(final?.status, 'ready');
  if (final?.status === 'ready') assert.equal(final.request.experiment.parameters?.energy, 3);
  runner.update({ ...settings, energy: undefined }, 0);
  assert.equal(states.at(-1)?.status, 'error');
  runner.dispose();
});
test('preset inputs preserve documented propagation and selected-point values come from the same record as the graph', () => {
  const layers = buildRequest(preset('layers'));
  assert.deepEqual(layers.experiment.layers, [
    { distance: 1, potential: 0.2 },
    { distance: 1, potential: 1.4 }
  ]);
  const resonance = buildRequest(preset('density'));
  assert.equal(resonance.axis, 'potential');
  assert.equal(resonance.experiment.layers[0].distance, 4.0336988686318564);
  const data = {
    results: [{ ideal: { electron: 1, other: 0 } }, { ideal: { electron: 0.3, other: 0.7 } }]
  } as NeutrinoResponse;
  assert.equal(curveValues(data, 'other', 'ideal')[1], data.results[1].ideal.other);
});
