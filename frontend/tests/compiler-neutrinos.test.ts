import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createApiClient } from '../src/api/client.ts';
import { neutrinoTimings } from '../src/lib/presentation/neutrinos.ts';

test('science compiler transport preserves source and uses the scientific endpoints only', async () => {
  const source = '@qatlas.neutrino\ndef model(): return {"experiment":{"layers":[{"distance":1}]}}';
  const seen: { url: string; init?: RequestInit }[] = [];
  const client = createApiClient({
    baseUrl: 'http://test/api',
    fetcher: async (url, init) => {
      seen.push({ url: String(url), init });
      return Response.json({});
    }
  });
  await client.compileNeutrinos({ source });
  await client.benchmarkNeutrinos({ source });
  assert.deepEqual(
    seen.map((r) => r.url),
    ['http://test/api/compiler/neutrinos/generate', 'http://test/api/compiler/neutrinos/benchmark']
  );
  for (const call of seen) {
    assert.equal(call.init?.method, 'POST');
    assert.deepEqual(JSON.parse(String(call.init?.body)), { source });
  }
});

test('timing summary sums real point scopes without adding nested ideal or convergence work twice', () => {
  const result = neutrinoTimings([
    {
      timing_ms: {
        classical: 0.04,
        circuit_end_to_end: 12,
        ideal_execution: 3,
        convergence_check: 5
      }
    },
    {
      timing_ms: {
        classical: 0.06,
        circuit_end_to_end: 18,
        ideal_execution: 4,
        convergence_check: 7
      }
    }
  ]);
  assert.deepEqual(result, { classicalMs: 0.1, circuitMs: 30, idealMs: 7 });
});
