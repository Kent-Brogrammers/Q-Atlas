import type {
  BenchmarkEndpoint,
  BenchmarkResult,
  JsonObject,
  SolverResult
} from '../types/contracts.ts';

export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSolver(value: unknown): value is SolverResult | null {
  if (value === null) return true;
  return (
    isRecord(value) &&
    typeof value.algorithm === 'string' &&
    (value.objective === null ||
      (typeof value.objective === 'number' && Number.isFinite(value.objective))) &&
    (value.elapsed_ms === null ||
      (typeof value.elapsed_ms === 'number' &&
        Number.isFinite(value.elapsed_ms) &&
        value.elapsed_ms >= 0))
  );
}

export function parseBenchmark(value: unknown): BenchmarkResult {
  if (
    !isRecord(value) ||
    !['compiler', 'materials', 'optimization', 'search'].includes(String(value.experiment)) ||
    typeof value.problem_id !== 'string' ||
    typeof value.backend !== 'string' ||
    !isSolver(value.classical) ||
    !isSolver(value.quantum) ||
    !isRecord(value.metrics) ||
    !isRecord(value.metadata)
  ) {
    throw new ApiError('The backend response does not match the documented benchmark format.');
  }
  return value as unknown as BenchmarkResult;
}

/** No fallback to fixtures: a failed live request must remain a visible failure. */
export function createApiClient({
  baseUrl = '',
  fetcher = globalThis.fetch
}: {
  baseUrl?: string;
  fetcher?: typeof fetch;
} = {}) {
  return {
    async postBenchmark(endpoint: BenchmarkEndpoint, payload: JsonObject, signal?: AbortSignal) {
      // Request envelopes are deliberately caller-supplied until the team agrees on them.
      try {
        const response = await fetcher(`${baseUrl.replace(/\/$/, '')}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify(payload),
          signal: signal
            ? AbortSignal.any([signal, AbortSignal.timeout(15_000)])
            : AbortSignal.timeout(15_000)
        });
        if (!response.ok)
          throw new ApiError(`The backend returned HTTP ${response.status}.`, response.status);
        return parseBenchmark(await response.json());
      } catch (error) {
        if (error instanceof ApiError) throw error;
        if (error instanceof Error && ['AbortError', 'TimeoutError'].includes(error.name)) {
          throw new ApiError('The request was cancelled or timed out.');
        }
        throw new ApiError('The backend could not be reached or returned invalid JSON.');
      }
    }
  };
}
