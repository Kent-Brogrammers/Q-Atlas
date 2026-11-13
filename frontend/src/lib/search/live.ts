import { duration } from '../presentation/format.ts';
import type { SearchRequest, SearchResult } from '../../types/index.ts';
import { samplingInterval } from './uncertainty.ts';

export interface SearchSettings {
  numQubits: number | undefined;
  targets: string;
  automatic: boolean;
  iterations: number | undefined;
  shots: number | undefined;
  seed: number | undefined;
  timeout: number | undefined;
}

export function defaultSettings(): SearchSettings {
  return {
    numQubits: 3,
    targets: '001',
    automatic: true,
    iterations: 2,
    shots: 1024,
    seed: 42,
    timeout: 30
  };
}

function integer(value: number | undefined, min: number, max: number, label: string): number {
  if (value === undefined || !Number.isInteger(value) || value < min || value > max) {
    throw new Error(`${label} must be an integer from ${min} to ${max}.`);
  }
  return value;
}

export function buildRequest(settings: SearchSettings): SearchRequest {
  const width = integer(settings.numQubits, 1, 6, 'Qubits');
  const targets = settings.targets.trim().split(/[\s,]+/);
  if (
    targets.some((target) => target.length !== width || !/^[01]+$/.test(target)) ||
    new Set(targets).size !== targets.length
  ) {
    throw new Error(`Enter unique ${width}-bit targets, separated by commas or spaces.`);
  }
  if (
    settings.timeout === undefined ||
    !Number.isFinite(settings.timeout) ||
    settings.timeout <= 0 ||
    settings.timeout > 60
  ) {
    throw new Error('Timeout must be greater than zero and at most 60 seconds.');
  }
  return {
    num_qubits: width,
    marked_states: targets,
    iterations: settings.automatic ? null : integer(settings.iterations, 0, 32, 'Iterations'),
    config: {
      backend: 'aer_simulator',
      shots: integer(settings.shots, 1, 10000, 'Shots'),
      seed: integer(settings.seed, 0, 2 ** 32 - 1, 'Seed'),
      timeout_seconds: settings.timeout
    }
  };
}

export interface CurvePoint {
  iteration: number;
  measured: number | null;
  theoretical: number | null;
  observedRange?: [number, number];
  confidenceInterval?: [number, number];
}

export function curvePoints(results: SearchResult[]): CurvePoint[] {
  return results.map((result) => {
    const iteration = result.metadata.parameters.iterations;
    if (iteration == null || !Number.isInteger(iteration) || iteration < 0) {
      throw new Error('The backend did not report an effective iteration count.');
    }
    const measured = result.metrics.success_probability ?? null;
    const theoretical = result.metrics.theoretical_success_probability ?? null;
    for (const value of [measured, theoretical]) {
      if (value !== null && (!Number.isFinite(value) || value < 0 || value > 1)) {
        throw new Error('The backend reported an invalid probability.');
      }
    }
    const interval = measured === null ? null : samplingInterval(result);
    return {
      iteration,
      measured,
      theoretical,
      ...(interval ? { confidenceInterval: interval } : {})
    };
  });
}

export type SearchCall = (request: SearchRequest, signal?: AbortSignal) => Promise<SearchResult>;

export async function measureSweep(
  settings: SearchSettings,
  maxIteration: number | undefined,
  search: SearchCall,
  signal: AbortSignal,
  progress: (completed: number, total: number) => void = () => {}
): Promise<SearchResult[]> {
  const end = integer(maxIteration, 0, 12, 'Last curve iteration');
  const base = buildRequest({ ...settings, automatic: true });
  const results: SearchResult[] = [];
  for (let iteration = 0; iteration <= end; iteration++) {
    signal.throwIfAborted();
    const result = await search({ ...base, iterations: iteration }, signal);
    signal.throwIfAborted();
    curvePoints([result]);
    if (result.metadata.parameters.iterations !== iteration) {
      throw new Error('The backend returned a different curve iteration.');
    }
    results.push(result);
    progress(results.length, end + 1);
  }
  return results;
}

export function percentage(value: number | null | undefined): string {
  return value == null ? 'Not available' : `${(value * 100).toFixed(1)}%`;
}

export function milliseconds(value: number | null | undefined): string {
  return duration(value);
}
