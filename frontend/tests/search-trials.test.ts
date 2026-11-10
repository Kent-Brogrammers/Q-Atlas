import assert from 'node:assert/strict';
import { test } from 'node:test';
import { defaultSettings } from '../src/lib/search/live.ts';
import { measureTrials, summarizeTrials, trialCurve } from '../src/lib/search/trials.ts';
import type { SearchRequest, SearchResult, SolverResult } from '../src/types/index.ts';

// Synthetic records exercise aggregation only; never used by the application.
function fixture(seed: number, probability = 0.5, elapsed = 10): SearchResult {
  const solver = (time: number): SolverResult => ({
    algorithm: 'test',
    elapsed_ms: time,
    timing: {
      includes_queue: false,
      includes_sampling: false,
      includes_optimizer: false,
      includes_transpilation: false
    }
  });
  return {
    experiment: 'search',
    status: 'completed',
    problem_id: 'test-instance',
    backend: 'aer_simulator',
    classical: solver(elapsed / 10),
    quantum: solver(elapsed),
    metrics: { shots: 100, success_probability: probability, theoretical_success_probability: 0.5 },
    metadata: {
      seed,
      repetitions: 1,
      timing_scope: 'end_to_end',
      simulated: true,
      simulation_method: 'statevector',
      versions: { test: '1' },
      oracle_assumptions: 'Test fixture only',
      parameters: {
        num_qubits: 3,
        marked_states: ['001'],
        iterations: 2,
        config: { seed, shots: 100 }
      }
    }
  };
}

test('known records produce exact mean, sample deviation, range and odd median', () => {
  const records = [fixture(0, 0, 30), fixture(1, 0.5, 10), fixture(2, 1, 20)];
  const before = structuredClone(records);
  const summary = summarizeTrials(records);
  assert.equal(summary.meanSuccessProbability, 0.5);
  assert.equal(summary.sampleStandardDeviation, 0.5);
  assert.equal(summary.minimumSuccessProbability, 0);
  assert.equal(summary.maximumSuccessProbability, 1);
  assert.equal(summary.medianQuantumMs, 20);
  assert.equal(summary.medianClassicalMs, 2);
  assert.equal(summary.totalShots, 300);
  assert.equal(summary.shotsPerTrial, 100);
  assert.deepEqual(summary.seeds, [0, 1, 2]);
  assert.deepEqual(trialCurve(summary), [
    { iteration: 2, measured: 0.5, theoretical: 0.5, observedRange: [0, 1] }
  ]);
  assert.deepEqual(records, before);
});

test('even median, exact zero and perfect success are preserved', () => {
  for (const probability of [0, 1]) {
    const summary = summarizeTrials([fixture(0, probability, 0), fixture(1, probability, 20)]);
    assert.equal(summary.meanSuccessProbability, probability);
    assert.equal(summary.sampleStandardDeviation, 0);
    assert.equal(summary.minimumSuccessProbability, probability);
    assert.equal(summary.maximumSuccessProbability, probability);
    assert.equal(summary.medianQuantumMs, 10);
  }
});

test('missing runtime does not compute a biased subset median; missing theory stays missing', () => {
  const records = [fixture(0), fixture(1)];
  records[0].quantum = null;
  records[1].metrics.theoretical_success_probability = null;
  const summary = summarizeTrials(records);
  assert.equal(summary.medianQuantumMs, null);
  assert.equal(summary.medianClassicalMs, 1);
  assert.equal(summary.theoreticalSuccessProbability, null);
});

test('invalid or missing probabilities are not silently omitted', () => {
  for (const probability of [null, NaN, -0.1, 1.1]) {
    const records = [fixture(0), fixture(1)];
    records[1].metrics.success_probability = probability;
    assert.throws(() => summarizeTrials(records));
  }
});

test('mismatched instances, iterations, shots, versions, seeds and repetition metadata are rejected', () => {
  const corruptions: ((result: SearchResult) => void)[] = [
    (result) => {
      result.problem_id = 'different';
    },
    (result) => {
      result.metadata.parameters.marked_states = ['110'];
    },
    (result) => {
      result.metadata.parameters.iterations = 3;
    },
    (result) => {
      result.metrics.shots = 200;
    },
    (result) => {
      result.metadata.parameters.config!.shots = 200;
    },
    (result) => {
      result.metadata.timing_scope = 'solver_only';
    },
    (result) => {
      result.metadata.versions = { test: '2' };
    },
    (result) => {
      result.metadata.seed = 0;
      result.metadata.parameters.config!.seed = 0;
    },
    (result) => {
      result.metadata.seed = null;
    },
    (result) => {
      result.metadata.parameters.config!.seed = 99;
    },
    (result) => {
      result.metadata.repetitions = 2;
    },
    (result) => {
      result.metrics.theoretical_success_probability = 0.6;
    },
    (result) => {
      result.quantum!.elapsed_ms = Infinity;
    },
    (result) => {
      result.classical!.elapsed_ms = -1;
    }
  ];
  for (const corrupt of corruptions) {
    const record = fixture(1);
    corrupt(record);
    assert.throws(() => summarizeTrials([fixture(0), record]));
  }
});

test('two through five trials are required, with valid shot counts', () => {
  for (const length of [0, 1, 6]) {
    assert.throws(() => summarizeTrials(Array.from({ length }, (_, index) => fixture(index))));
  }
  for (const shots of [null, 0, 1.5, 10001]) {
    const records = [fixture(0), fixture(1)];
    for (const record of records) record.metrics.shots = shots;
    assert.throws(() => summarizeTrials(records));
  }
});

test('equivalent target and version ordering does not change aggregation', () => {
  const records = [fixture(0), fixture(1)];
  records[0].metadata.parameters.marked_states = ['001', '110'];
  records[1].metadata.parameters.marked_states = ['110', '001'];
  records[0].metadata.versions = { a: '1', b: '2' };
  records[1].metadata.versions = { b: '2', a: '1' };
  assert.equal(summarizeTrials(records).trialCount, 2);
});

test('repeated requests are sequential with distinct wrapped seeds and effective settings', async () => {
  const requests: SearchRequest[] = [];
  const progress: number[][] = [];
  let active = 0,
    maximumActive = 0;
  const settings = { ...defaultSettings(), seed: 2 ** 32 - 1, automatic: false, iterations: 2 };
  const before = structuredClone(settings);
  const signal = new AbortController().signal;
  const records = await measureTrials(
    settings,
    3,
    async (request, receivedSignal) => {
      assert.equal(receivedSignal, signal);
      active++;
      maximumActive = Math.max(active, maximumActive);
      await Promise.resolve();
      active--;
      requests.push(request);
      const result = fixture(request.config!.seed!);
      result.metrics.shots = request.config!.shots;
      result.metadata.parameters = structuredClone(request);
      return result;
    },
    signal,
    (done, total) => progress.push([done, total])
  );
  assert.equal(maximumActive, 1);
  assert.deepEqual(
    requests.map((request) => request.config!.seed),
    [2 ** 32 - 1, 0, 1]
  );
  assert.deepEqual(progress, [
    [1, 3],
    [2, 3],
    [3, 3]
  ]);
  assert.equal(records.length, 3);
  assert.deepEqual(settings, before);
  assert.ok(
    requests.every((request) => request.iterations === 2 && request.config!.shots === 1024)
  );
});

test('automatic iterations remain backend-selected for each seeded trial', async () => {
  const records = await measureTrials(
    defaultSettings(),
    2,
    async (request) => {
      assert.equal(request.iterations, null);
      const result = fixture(request.config!.seed!);
      result.metrics.shots = request.config!.shots;
      result.metadata.parameters = { ...request, iterations: 2 };
      return result;
    },
    new AbortController().signal
  );
  assert.equal(summarizeTrials(records).iteration, 2);
});

test('invalid trial counts and settings send no requests', async () => {
  for (const count of [0, 1, 6, 2.5, undefined]) {
    await assert.rejects(
      measureTrials(
        defaultSettings(),
        count,
        async () => {
          assert.fail('must not send request');
        },
        new AbortController().signal
      )
    );
  }
  await assert.rejects(
    measureTrials(
      { ...defaultSettings(), targets: '' },
      3,
      async () => {
        assert.fail('must not send invalid settings');
      },
      new AbortController().signal
    )
  );
});

test('failed trials stop the batch without returning a partial summary', async () => {
  let calls = 0;
  await assert.rejects(
    measureTrials(
      defaultSettings(),
      3,
      async (request) => {
        if (++calls === 2) throw new Error('simulator failed');
        const result = fixture(request.config!.seed!);
        result.metadata.parameters = { ...request, iterations: 2 };
        result.metrics.shots = request.config!.shots;
        return result;
      },
      new AbortController().signal
    ),
    /simulator failed/
  );
  assert.equal(calls, 2);
});

test('cancellation prevents initial or later requests and discards late responses', async () => {
  const before = new AbortController();
  before.abort();
  await assert.rejects(
    measureTrials(
      defaultSettings(),
      3,
      async () => {
        assert.fail('cancelled batch must not start');
      },
      before.signal
    ),
    { name: 'AbortError' }
  );
  const during = new AbortController();
  let calls = 0;
  await assert.rejects(
    measureTrials(
      defaultSettings(),
      3,
      async (request) => {
        calls++;
        during.abort();
        return fixture(request.config!.seed!);
      },
      during.signal
    ),
    { name: 'AbortError' }
  );
  assert.equal(calls, 1);
});

test('a mismatched response seed fails immediately', async () => {
  let calls = 0;
  await assert.rejects(
    measureTrials(
      defaultSettings(),
      3,
      async () => {
        calls++;
        return fixture(99);
      },
      new AbortController().signal
    ),
    /different trial seed/
  );
  assert.equal(calls, 1);
});
