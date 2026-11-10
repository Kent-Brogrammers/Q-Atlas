import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import {
  buildSearchExport,
  loadRecordedDemo,
  parseRecordedDemo
} from '../src/lib/search/recorded.ts';
import { summarizeTrials } from '../src/lib/search/trials.ts';

function recording() {
  return JSON.parse(
    readFileSync(new URL('../src/lib/search/previously-measured.json', import.meta.url), 'utf8')
  );
}

test('real recorded curve and trials load with explicit provenance', () => {
  const curve = loadRecordedDemo('curve');
  const trials = loadRecordedDemo('trials');
  assert.equal(curve.results.length, 7);
  assert.equal(trials.results.length, 3);
  assert.equal(curve.provenance.recording_method, 'local_fastapi_testclient');
  assert.ok(Number.isFinite(Date.parse(curve.provenance.recorded_at_utc)));
  assert.deepEqual(summarizeTrials(trials.results).seeds, [42, 43, 44]);
});

test('loading a recording returns independent copies and preserves zero iterations', () => {
  const first = loadRecordedDemo('curve');
  assert.equal(first.results[0].metadata.parameters.iterations, 0);
  assert.equal(first.results[0].metrics.quantum_total_oracle_queries, 0);
  first.results[0].metadata.parameters.marked_states[0] = '111';
  first.provenance.source_revision = 'changed';
  const second = loadRecordedDemo('curve');
  assert.deepEqual(second.results[0].metadata.parameters.marked_states, ['001']);
  assert.notEqual(second.provenance.source_revision, 'changed');
});

test('missing provenance or incomplete files never load as measured results', () => {
  for (const patch of [
    { source: 'live_search_api' },
    { bundle_version: 2 },
    { source_revision: '' },
    { recorded_at_utc: 'not a date' },
    { recorded_at_utc: '2026-11-10T12:00:00' },
    { source_sha256: {} },
    { environment: {} },
    { working_tree_dirty: 'false' },
    { curve: [] },
    { trials: [] }
  ])
    assert.throws(
      () => parseRecordedDemo({ ...recording(), ...patch }, 'curve'),
      /invalid or incomplete/
    );
  for (const value of [null, {}, [], 'demo'])
    assert.throws(() => parseRecordedDemo(value, 'curve'));
});

test('tampered probabilities, counts, settings and seeds are rejected', () => {
  const corruptions = [
    (data: ReturnType<typeof recording>) => {
      data.curve[2].metrics.successful_shots = 0;
    },
    (data: ReturnType<typeof recording>) => {
      data.curve[2].metrics.quantum_total_oracle_queries = 1;
    },
    (data: ReturnType<typeof recording>) => {
      data.curve[2].metrics.classical_observed_queries = 99;
    },
    (data: ReturnType<typeof recording>) => {
      data.curve[2].metadata.parameters.marked_states = ['111'];
    },
    (data: ReturnType<typeof recording>) => {
      data.trials[1].metadata.seed = 42;
    },
    (data: ReturnType<typeof recording>) => {
      data.trials[0].metadata.versions = {};
    }
  ];
  for (const corrupt of corruptions) {
    const data = recording();
    corrupt(data);
    assert.throws(() => parseRecordedDemo(data, 'trials'), /invalid or incomplete/);
  }
});

test('recorded exports can retain their source, timestamp and all raw trial evidence', () => {
  const saved = loadRecordedDemo('trials');
  const exported = JSON.parse(
    JSON.stringify(buildSearchExport('trials', saved.results, saved.provenance))
  );
  assert.equal(exported.source, 'previously_measured_search_demo');
  assert.equal(exported.recording.recorded_at_utc, saved.provenance.recorded_at_utc);
  assert.equal(exported.results.length, 3);
  assert.deepEqual(exported.trial_summary.seeds, [42, 43, 44]);
});

test('live exports retain their live source and never acquire recorded provenance', () => {
  const results = loadRecordedDemo('curve').results;
  const exported = buildSearchExport('curve', results, null);
  assert.equal(exported.source, 'live_search_api');
  assert.equal(exported.recording, null);
  assert.equal(exported.trial_summary, null);
  exported.results[0].metadata.seed = 999;
  assert.equal(results[0].metadata.seed, 42);
});

test('export supports reactive proxies used by the page and returns independent JSON data', () => {
  const saved = loadRecordedDemo('trials');
  const reactiveResults = new Proxy(saved.results, {});
  const reactiveProvenance = new Proxy(saved.provenance, {});
  const exported = buildSearchExport('trials', reactiveResults, reactiveProvenance);
  assert.equal(exported.source, 'previously_measured_search_demo');
  assert.equal(exported.results.length, 3);
  assert.equal(exported.trial_summary?.trialCount, 3);
  exported.results[0].metadata.seed = 999;
  assert.equal(saved.results[0].metadata.seed, 42);
});
