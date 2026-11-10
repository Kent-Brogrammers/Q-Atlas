import type { SearchResult } from '../../types/index.ts';
import { buildRequest, curvePoints } from './live.ts';
import type { CurvePoint, SearchCall, SearchSettings } from './live.ts';

export interface TrialSummary {
  trialCount: number;
  iteration: number;
  seeds: number[];
  shotsPerTrial: number;
  totalShots: number;
  meanSuccessProbability: number;
  minimumSuccessProbability: number;
  maximumSuccessProbability: number;
  sampleStandardDeviation: number;
  theoreticalSuccessProbability: number | null;
  medianClassicalMs: number | null;
  medianQuantumMs: number | null;
}

function trialCount(value: number | undefined): number {
  if (value === undefined || !Number.isInteger(value) || value < 2 || value > 5) {
    throw new Error('Repeated trials must be an integer from 2 to 5.');
  }
  return value;
}

function median(values: (number | null | undefined)[]): number | null {
  // Do not report a median of a silently reduced subset when timings are missing.
  if (values.some((value) => value == null)) return null;
  const sorted = (values as number[]).toSorted((a, b) => a - b);
  if (sorted.some((value) => !Number.isFinite(value) || value < 0)) {
    throw new Error('The backend reported an invalid runtime.');
  }
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function instanceSignature(result: SearchResult): string {
  const parameters = result.metadata.parameters;
  return JSON.stringify({
    problem: result.problem_id,
    backend: result.backend,
    simulated: result.metadata.simulated,
    method: result.metadata.simulation_method,
    timingScope: result.metadata.timing_scope,
    width: parameters.num_qubits,
    targets: [...parameters.marked_states].sort(),
    iteration: parameters.iterations,
    shots: result.metrics.shots,
    versions: Object.entries(result.metadata.versions ?? {}).sort(([a], [b]) => a.localeCompare(b))
  });
}

export function summarizeTrials(results: SearchResult[]): TrialSummary {
  const count = trialCount(results.length);
  const points = curvePoints(results);
  const first = results[0];
  const signature = instanceSignature(first);
  const shots = first.metrics.shots;
  if (shots == null || !Number.isInteger(shots) || shots < 1 || shots > 10000) {
    throw new Error('Repeated results must report a valid shot count.');
  }
  const seeds: number[] = [];
  for (const result of results) {
    if (
      instanceSignature(result) !== signature ||
      result.metadata.repetitions !== 1 ||
      result.metadata.parameters.config?.shots !== shots
    ) {
      throw new Error(
        'Repeated trials must have the same instance, iterations, shots and versions.'
      );
    }
    const seed = result.metadata.seed;
    if (
      seed == null ||
      !Number.isInteger(seed) ||
      seed < 0 ||
      seed > 2 ** 32 - 1 ||
      seed !== result.metadata.parameters.config?.seed ||
      seeds.includes(seed)
    ) {
      throw new Error('Every trial must record a distinct matching simulator seed.');
    }
    seeds.push(seed);
  }
  const probabilities = points.map((point) => {
    if (point.measured === null) throw new Error('Repeated trials require measured probabilities.');
    return point.measured;
  });
  const theory = points.map((point) => point.theoretical);
  const availableTheory = theory.filter((value): value is number => value !== null);
  if (availableTheory.some((value) => Math.abs(value - availableTheory[0]) > 1e-12)) {
    throw new Error('Repeated trials reported inconsistent theoretical probabilities.');
  }
  const mean = probabilities.reduce((sum, value) => sum + value, 0) / count;
  return {
    trialCount: count,
    iteration: points[0].iteration,
    seeds,
    shotsPerTrial: shots,
    totalShots: count * shots,
    meanSuccessProbability: mean,
    minimumSuccessProbability: Math.min(...probabilities),
    maximumSuccessProbability: Math.max(...probabilities),
    sampleStandardDeviation: Math.sqrt(
      probabilities.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (count - 1)
    ),
    theoreticalSuccessProbability: availableTheory.length === count ? availableTheory[0] : null,
    medianClassicalMs: median(results.map((result) => result.classical?.elapsed_ms)),
    medianQuantumMs: median(results.map((result) => result.quantum?.elapsed_ms))
  };
}

export function trialCurve(summary: TrialSummary): CurvePoint[] {
  return [
    {
      iteration: summary.iteration,
      measured: summary.meanSuccessProbability,
      theoretical: summary.theoreticalSuccessProbability,
      observedRange: [summary.minimumSuccessProbability, summary.maximumSuccessProbability]
    }
  ];
}

export async function measureTrials(
  settings: SearchSettings,
  repetitions: number | undefined,
  search: SearchCall,
  signal: AbortSignal,
  progress: (completed: number, total: number) => void = () => {}
): Promise<SearchResult[]> {
  const count = trialCount(repetitions);
  const base = buildRequest(settings);
  const results: SearchResult[] = [];
  for (let index = 0; index < count; index++) {
    signal.throwIfAborted();
    const seed = (base.config!.seed! + index) % 2 ** 32;
    const request = { ...base, config: { ...base.config, seed } };
    const result = await search(request, signal);
    signal.throwIfAborted();
    if (result.metadata.seed !== seed || result.metadata.parameters.config?.seed !== seed) {
      throw new Error('The backend returned a different trial seed.');
    }
    const actual = result.metadata.parameters;
    if (
      actual.num_qubits !== request.num_qubits ||
      JSON.stringify([...actual.marked_states].sort()) !==
        JSON.stringify([...request.marked_states].sort()) ||
      result.metrics.shots !== request.config.shots ||
      (request.iterations != null && actual.iterations !== request.iterations)
    ) {
      throw new Error('The backend returned a different repeated-trial configuration.');
    }
    curvePoints([result]);
    results.push(result);
    progress(results.length, count);
  }
  summarizeTrials(results);
  return results;
}
