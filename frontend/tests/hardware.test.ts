import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createApiClient } from '../src/api/client.ts';
import {
  canStartAnother,
  canSubmit,
  hardwareTask,
  makeRequest,
  pickHardwareJob
} from '../src/lib/hardware/requests.ts';
import { loadPhysicalRecording } from '../src/lib/hardware/recorded.ts';
import { cycleProblem } from '../src/lib/studies/model.ts';
import type { HardwareJob, NeutrinoRequest, SearchRequest } from '../src/types/index.ts';

const search: SearchRequest = {
  num_qubits: 3,
  marked_states: ['001'],
  iterations: 2,
  config: { shots: 1024, seed: 42 }
};
const id = '50000000-0000-4000-8000-000000000000';
function job(status = 'SUBMITTED'): HardwareJob {
  return {
    request_id: id,
    task: { kind: 'search', parameters: search },
    problem_id: 'test-only',
    created_at_utc: '2026-11-12T00:00:00Z',
    updated_at_utc: '2026-11-12T00:00:00Z',
    status,
    shots: 128,
    max_execution_seconds: 10,
    job_id: 'mock-provider-job',
    simulated: false
  };
}

test('QPU settings retain the scientific instance and explicitly bound shots/resolution', () => {
  const before = structuredClone(search);
  const task = hardwareTask('search', search, 128, 3, 4, 1);
  assert.deepEqual(search, before);
  assert.equal(task.kind, 'search');
  if (task.kind === 'search') {
    assert.equal(task.parameters.config!.shots, 128);
    assert.deepEqual(task.parameters.marked_states, ['001']);
  }
  const optimization = hardwareTask(
    'optimization',
    { problem: cycleProblem(4), config: { p: 8 } },
    128,
    3,
    4,
    2
  );
  if (optimization.kind === 'optimization') {
    assert.deepEqual(optimization.parameters.problem, cycleProblem(4));
    assert.equal(optimization.parameters.config!.p, 2);
    assert.equal(optimization.parameters.config!.max_iterations, 20);
  }
  const materials = hardwareTask(
    'materials',
    { num_spins: 3, coupling: 0.5, field: 0.7, evolution_time: 2, trotter_steps: 32 },
    64,
    3,
    4,
    1
  );
  if (materials.kind === 'materials') {
    assert.equal(materials.parameters.evolution_time, 2);
    assert.equal(materials.parameters.coupling, 0.5);
    assert.equal(materials.parameters.trotter_steps, 4);
    assert.equal(materials.parameters.time_samples, 3);
  }
  assert.throws(() => hardwareTask('search', search, 129, 3, 4, 1), /1–128/);
});

test('neutrino hardware curves preserve parameters and profile while selecting bounded samples', () => {
  const base: NeutrinoRequest = {
    experiment: {
      parameters: { theta: 0.2 },
      layers: [{ distance: 4, potential: 0.9 }],
      shots: 4096
    },
    samples: 21,
    axis: 'potential'
  };
  const task = hardwareTask('neutrinos', base, 128, 3, 4, 1);
  if (task.kind === 'neutrinos') {
    assert.equal(task.parameters.samples, 3);
    assert.equal(task.parameters.experiment.shots, 128);
    assert.deepEqual(task.parameters.experiment.layers, base.experiment.layers);
  }
  assert.equal(base.samples, 21);
});

test('pending and uncertain acknowledgements cannot create another submission', () => {
  assert.equal(canSubmit(null, ''), true);
  assert.equal(canSubmit(null, id), false);
  for (const state of ['PREPARING', 'SUBMISSION_UNKNOWN', 'SUBMITTED', 'RUNNING', 'DONE']) {
    assert.equal(canSubmit(job(state), id), false);
  }
  assert.equal(canStartAnother({ ...job('DONE'), measurement_complete: true }), true);
  assert.equal(canSubmit(job('FAILED_BEFORE_SUBMISSION'), id), true);
  assert.equal(canSubmit(job('CANCELLED'), 'different-id'), false);
});

test('a shared job selects the experiment-specific evidence and keeps shared usage explicit', () => {
  const child = {
    ...job('DONE'),
    measurement_complete: true,
    shared_job_timings: { quantum_seconds: 2 }
  };
  const parent: HardwareJob = {
    ...job('DONE'),
    task: {
      kind: 'suite',
      parameters: [child.task as Extract<HardwareJob['task'], { kind: 'search' }>]
    },
    children: [child]
  };
  assert.equal(pickHardwareJob(parent, 'search'), child);
  assert.equal(pickHardwareJob(parent, 'suite'), parent);
  assert.equal(child.shared_job_timings.quantum_seconds, 2);
  assert.equal(makeRequest(parent.task, id, '', 64).shots, 64);
});

test('recorded physical fallback retains real provenance and clones the archived evidence', () => {
  const suite = loadPhysicalRecording('suite');
  assert.equal(suite.simulated, false);
  assert.equal(suite.job_id, 'dbr0sthabdes73fp2v60');
  assert.equal(suite.children!.length, 5);
  for (const kind of ['compiler', 'optimization', 'materials', 'search', 'neutrinos'] as const) {
    const child = loadPhysicalRecording(kind);
    assert.equal(child.task.kind, kind);
    assert.equal(child.measurement_complete, true);
    assert.ok(child.counts!.length > 0);
    assert.equal(child.shared_job_timings!.quantum_seconds, 2);
  }
  suite.children![0].counts![0] = {};
  assert.ok(Object.keys(loadPhysicalRecording('compiler').counts![0]).length > 0);
});

test('physical submissions, recovery and cancellation use the additive endpoints without credentials in requests', async () => {
  const seen: { url: string; init?: RequestInit }[] = [];
  const client = createApiClient({
    baseUrl: 'http://test/api',
    fetcher: async (url, init) => {
      seen.push({ url: String(url), init });
      return Response.json(job());
    }
  });
  const body = makeRequest({ kind: 'search', parameters: search }, id, 'ibm_test');
  await client.submitHardware(body);
  await client.hardwareJob(id);
  await client.cancelHardwareJob(id);
  assert.deepEqual(
    seen.map((r) => r.url),
    [
      `http://test/api/hardware/submit`,
      `http://test/api/hardware/jobs/${id}`,
      `http://test/api/hardware/jobs/${id}/cancel`
    ]
  );
  assert.equal(JSON.parse(String(seen[0].init!.body)).confirmed, true);
  assert.equal(seen[1].init!.method, 'GET');
  assert.equal(seen[2].init!.method, 'POST');
  assert.ok(!String(seen[0].init!.body).includes('QUANTUM-KEY'));
});
