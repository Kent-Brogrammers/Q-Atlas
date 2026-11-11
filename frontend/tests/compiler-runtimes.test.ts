import assert from 'node:assert/strict';
import { test } from 'node:test';
import { runtimeMeasurements } from '../src/compiler/runtimes.ts';

test('runtime comparison converts provider seconds into the same units as classical time', () => {
  const readings = runtimeMeasurements(0.015, 2);
  assert.equal(readings[0].milliseconds, 0.015);
  assert.equal(readings[1].milliseconds, 2000);
  assert.deepEqual(
    readings.map((reading) => reading.kind),
    ['classical', 'qpu']
  );
});

test('unknown and invalid timings never appear as measured bars', () => {
  for (const missing of [undefined, null, NaN, Infinity, -1]) {
    assert.deepEqual(runtimeMeasurements(missing, missing), []);
  }
  assert.equal(runtimeMeasurements(1, null).length, 1);
  assert.equal(runtimeMeasurements(null, 2).length, 1);
  assert.deepEqual(runtimeMeasurements(null, Number.MAX_VALUE), []);
});

test('a reported zero remains a real measurement', () => {
  assert.deepEqual(
    runtimeMeasurements(0, 0).map((reading) => reading.milliseconds),
    [0, 0]
  );
});
