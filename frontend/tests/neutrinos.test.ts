import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  displaySeries,
  exportSettings,
  formatValue,
  initialSettings,
  probabilityPath,
  settingsErrors
} from '../src/lib/neutrinos/presentation.ts';
import type { ProposedNeutrinoResult } from '../src/lib/neutrinos/proposal.ts';
import { experiments } from '../src/lib/data/experiments.ts';
import { primaryNavigation } from '../src/lib/data/navigation.ts';

// Synthetic display-contract fixture only. Never imported by the application.
function displayFixture(): ProposedNeutrinoResult {
  return {
    status: 'completed',
    experiment: 'neutrinos',
    problem_id: 'test-only',
    backend: 'aer_simulator',
    model: {
      id: 'test-two-states',
      label: 'Test model',
      description: 'Display test only',
      flavors: [
        { id: 'electron', label: 'Electron', symbol: 'νe' },
        { id: 'muon', label: 'Muon', symbol: 'νμ' }
      ],
      initial_flavor_ids: ['electron'],
      environments: ['vacuum'],
      assumptions: ['Synthetic test data']
    },
    parameters: {
      model_id: 'test-two-states',
      initial_flavor_id: 'electron',
      energy_gev: 1,
      distance_km: 1000,
      distance_samples: 3,
      environment: { kind: 'vacuum' },
      config: {}
    },
    classical: null,
    quantum: null,
    distances_km: [0, 500, 1000],
    series: [
      {
        flavor_id: 'electron',
        classical: [1, 0.75, 0.5],
        qiskit: [1, 0.75, 0.5],
        absolute_error: [0, 0, 0]
      },
      {
        flavor_id: 'muon',
        classical: [0, 0.25, 0.5],
        qiskit: [0, 0.25, 0.5],
        absolute_error: [0, 0, 0]
      },
      { flavor_id: 'tau', classical: [0, 0, 0], qiskit: [0, 0, 0], absolute_error: [0, 0, 0] }
    ],
    metrics: {
      num_qubits: null,
      circuit_depth: null,
      shots_per_point: null,
      total_shots: null,
      max_absolute_error: null,
      rms_error: null,
      normalization_deviation: null,
      error_tolerance: null,
      within_tolerance: null
    },
    metadata: {
      seed: 42,
      timing_scope: 'solver_only',
      simulated: true,
      simulation_method: 'statevector',
      classical_method: 'Test only',
      qiskit_method: 'Test only',
      probability_method: 'statevector',
      parameter_source: 'Test only',
      physics_parameters: {},
      state_encoding: {},
      unused_state_policy: 'Test only',
      circuit_depth_scope: 'Test only',
      assumptions: ['Synthetic fixture']
    }
  };
}

test('primary navigation exposes the compiler and neutrino lab while retaining the experiment catalog', () => {
  assert.deepEqual(
    primaryNavigation.map(({ href, title }) => [href, title]),
    [
      ['/', 'Overview'],
      ['/compiler/', 'Python Compiler'],
      ['/neutrinos/', 'Neutrino Lab'],
      ['/search/', 'Grover Search'],
      ['/methodology/', 'Methodology']
    ]
  );
  for (const id of ['neutrinos', 'materials', 'optimization', 'compiler', 'search'])
    assert.equal(experiments.filter((item) => item.id === id).length, 1);
});

test('the initial configuration assumes neither a model nor an initial flavor', () => {
  const draft = initialSettings();
  assert.equal(draft.model_id, null);
  assert.equal(draft.initial_flavor_id, null);
  assert.equal(draft.density_g_cm3, undefined);
  assert.deepEqual(settingsErrors(draft), []);
  const exportData = exportSettings(draft);
  assert.equal(exportData.kind, 'neutrino_configuration_draft');
  assert.equal(exportData.contract_status, 'proposal_not_approved');
  assert.equal('results' in exportData, false);
});

test('vacuum settings never export stale matter parameters', () => {
  const draft = { ...initialSettings(), density_g_cm3: 3, electron_fraction: 0.5 };
  const before = structuredClone(draft);
  assert.deepEqual(exportSettings(draft).environment, { kind: 'vacuum' });
  assert.deepEqual(draft, before);
});

test('constant-density settings require explicit finite density and electron fraction', () => {
  const draft = initialSettings();
  draft.environment_kind = 'constant_density';
  assert.equal(settingsErrors(draft).length, 2);
  assert.throws(() => exportSettings(draft), /density/);
  draft.density_g_cm3 = 3;
  draft.electron_fraction = 0.5;
  assert.deepEqual(settingsErrors(draft), []);
  assert.deepEqual(exportSettings(draft).environment, {
    kind: 'constant_density',
    density_g_cm3: 3,
    electron_fraction: 0.5
  });
  draft.electron_fraction = 1.1;
  assert.match(settingsErrors(draft).join(), /Electron fraction/);
});

test('invalid inputs cannot be exported and zero baseline remains valid', () => {
  const draft = initialSettings();
  draft.energy_gev = NaN;
  draft.distance_km = -1;
  draft.requested_shots = 1.5;
  assert.equal(settingsErrors(draft).length, 3);
  assert.throws(() => exportSettings(draft));
  assert.deepEqual(settingsErrors({ ...initialSettings(), distance_km: 0 }), []);
});

test('missing results have no flavor series, rather than three zero-filled channels', () => {
  assert.deepEqual(displaySeries(null), []);
});

test('only backend-declared flavors are plotted; tau is not assumed', () => {
  const result = displayFixture();
  assert.deepEqual(
    displaySeries(result).map((series) => series.flavor.id),
    ['electron', 'muon']
  );
  result.model.flavors.push({ id: 'tau', label: 'Tau', symbol: 'ντ' });
  assert.equal(displaySeries(result).length, 3);
});

test('declared channels with missing series are not synthesized', () => {
  const result = displayFixture();
  result.series = result.series.filter((series) => series.flavor_id !== 'muon');
  assert.deepEqual(
    displaySeries(result).map((series) => series.flavor.id),
    ['electron']
  );
});

test('physical zero probabilities and missing samples remain distinct', () => {
  const result = displayFixture();
  result.series[1].qiskit = [0, null, 0.5];
  const muon = displaySeries(result).find((series) => series.flavor.id === 'muon')!;
  assert.equal(muon.values.qiskit[0], 0);
  assert.equal(muon.values.qiskit[1], null);
  assert.equal(probabilityPath([0, 500, 1000], [0, null, 1], 1000), 'M64,272 M818,42');
});

for (const [name, corrupt] of [
  [
    'misaligned arrays',
    (result: ProposedNeutrinoResult) => {
      result.series[0].qiskit = [0];
    }
  ],
  [
    'nonfinite probabilities',
    (result: ProposedNeutrinoResult) => {
      result.series[0].qiskit[1] = NaN;
    }
  ],
  [
    'out-of-range probabilities',
    (result: ProposedNeutrinoResult) => {
      result.series[0].qiskit[1] = 1.01;
    }
  ],
  [
    'duplicate flavor series',
    (result: ProposedNeutrinoResult) => {
      result.series.push(structuredClone(result.series[0]));
    }
  ]
] as const) {
  test(`${name} are not silently repaired for display`, () => {
    const result = displayFixture();
    corrupt(result);
    assert.deepEqual(
      displaySeries(result).map((series) => series.flavor.id),
      ['muon']
    );
  });
}

test('invalid or unordered propagation grids produce no curves', () => {
  const result = displayFixture();
  result.distances_km = [0, 1000, 500];
  assert.deepEqual(displaySeries(result), []);
  result.distances_km = [0, Infinity, 1000];
  assert.deepEqual(displaySeries(result), []);
});

test('unavailable accuracy stays unavailable while a measured zero stays zero', () => {
  assert.equal(formatValue(null), '—');
  assert.equal(formatValue(undefined), '—');
  assert.equal(formatValue(NaN), '—');
  assert.equal(formatValue(0), '0');
  assert.equal(formatValue(0.0000001), '1.00e-7');
  assert.equal(formatValue(0.123456), '0.123456');
});
