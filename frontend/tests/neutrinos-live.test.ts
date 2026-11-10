import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildRequest, defaultSettings } from '../src/lib/neutrinos/live.ts';
import { ApiError, createApiClient } from '../src/api/client.ts';

test('vacuum request uses normalized inputs and excludes stale matter potential', () => {
  const settings = defaultSettings();
  settings.potential = 3;
  const request = buildRequest(settings);
  assert.equal(request.axis, 'distance');
  assert.deepEqual(request.experiment.layers, [{ distance: 4, potential: 0 }]);
  assert.equal(request.experiment.parameters?.theta, 0.2);
  assert.equal('energy_gev' in request, false);
});

test('layer requests preserve order and split the configured total distance', () => {
  const request = buildRequest({
    ...defaultSettings(),
    environment: 'layers',
    potential: 0.2,
    second_potential: 1.4
  });
  assert.deepEqual(request.experiment.layers, [
    { distance: 2, potential: 0.2 },
    { distance: 2, potential: 1.4 }
  ]);
});

test('density sweep keeps a fixed baseline and requests the potential axis', () => {
  const request = buildRequest({ ...defaultSettings(), environment: 'density' });
  assert.equal(request.axis, 'potential');
  assert.equal(request.experiment.layers.length, 1);
  assert.equal(request.max_potential, defaultSettings().max_potential);
});

test('invalid settings are rejected before transport', () => {
  for (const patch of [
    { energy: 0 },
    { distance: NaN },
    { theta: undefined },
    { shots: 1.5 },
    { shots: 100000 },
    { seed: -1 }
  ])
    assert.throws(() => buildRequest({ ...defaultSettings(), ...patch }));
  assert.equal(
    buildRequest({ ...defaultSettings(), distance: 0 }).experiment.layers[0].distance,
    0
  );
});

test('neutrino transport sends typed settings to the registered endpoint', async () => {
  const request = buildRequest(defaultSettings());
  const response = {
    model: 'effective_two_flavor',
    units: 'normalized',
    axis: 'distance',
    coordinates: [],
    results: []
  };
  const fetcher: typeof fetch = async (url, init) => {
    assert.equal(url, 'http://localhost:8000/api/neutrinos/run');
    assert.equal(init?.method, 'POST');
    assert.deepEqual(JSON.parse(String(init?.body)), request);
    return Response.json(response);
  };
  assert.deepEqual(
    await createApiClient({ baseUrl: 'http://localhost:8000/api', fetcher }).neutrinos(request),
    response
  );
});

test('neutrino errors never fall back to sample results', async () => {
  const request = buildRequest(defaultSettings());
  const fetcher: typeof fetch = async () =>
    Response.json(
      {
        status: 'error',
        error: { code: 'TIMEOUT', message: 'Simulation timed out.', diagnostics: [] }
      },
      { status: 504 }
    );
  await assert.rejects(
    createApiClient({ fetcher }).neutrinos(request),
    (error: unknown) => error instanceof ApiError && error.status === 504
  );
  await assert.rejects(
    createApiClient({
      fetcher: async () => {
        throw new TypeError('offline');
      }
    }).neutrinos(request),
    /could not be reached/
  );
});
