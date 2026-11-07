import type {
  CompilerAnalyzeRequest,
  CompilerAnalyzeResult,
  CompilerBenchmarkRequest,
  CompilerBenchmarkResult,
  ErrorResponse,
  HealthResponse,
  MaterialsRequest,
  MaterialsResult,
  OptimizationRequest,
  OptimizationResult,
  SearchRequest,
  SearchResult
} from '../types/index.ts';

export class ApiError extends Error {
  readonly status: number;
  readonly body: ErrorResponse;

  constructor(status: number, body: ErrorResponse) {
    super(body.error.message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

interface BenchmarkRequests {
  '/api/compiler/benchmark': CompilerBenchmarkRequest;
  '/api/optimization/run': OptimizationRequest;
  '/api/search/run': SearchRequest;
  '/api/materials/run': MaterialsRequest;
}
interface BenchmarkResults {
  '/api/compiler/benchmark': CompilerBenchmarkResult;
  '/api/optimization/run': OptimizationResult;
  '/api/search/run': SearchResult;
  '/api/materials/run': MaterialsResult;
}

/** Typed transport shared by SvelteKit and the retained React scaffold.
 * FastAPI owns runtime request/response validation. No error falls back to example data.
 */
export function createApiClient({
  baseUrl = import.meta.env?.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api',
  fetcher = globalThis.fetch
}: { baseUrl?: string; fetcher?: typeof fetch } = {}) {
  async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    try {
      const response = await fetcher(`${baseUrl.replace(/\/$/, '')}${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: signal
          ? AbortSignal.any([signal, AbortSignal.timeout(65_000)])
          : AbortSignal.timeout(65_000)
      });
      const fallback: ErrorResponse = {
        status: 'error',
        error: {
          code: 'HTTP_ERROR',
          message: `API request failed (HTTP ${response.status}).`,
          diagnostics: []
        }
      };
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        if (!response.ok) throw new ApiError(response.status, fallback);
        throw new Error('The backend returned invalid JSON.');
      }
      if (!response.ok) {
        // Error envelopes are produced and sanitized by FastAPI's shared handlers.
        const error = payload as Partial<ErrorResponse> | null;
        throw new ApiError(
          response.status,
          error?.status === 'error' && typeof error.error?.message === 'string'
            ? (error as ErrorResponse)
            : fallback
        );
      }
      return payload as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (error instanceof Error && ['AbortError', 'TimeoutError'].includes(error.name)) {
        throw new Error('The request was cancelled or timed out.');
      }
      throw new Error('The backend could not be reached or returned invalid JSON.');
    }
  }
  function postBenchmark<E extends keyof BenchmarkRequests>(
    endpoint: E,
    body: BenchmarkRequests[E],
    signal?: AbortSignal
  ) {
    return request<BenchmarkResults[E]>(endpoint.slice('/api'.length), body, signal);
  }
  return {
    health: (signal?: AbortSignal) => request<HealthResponse>('/health', undefined, signal),
    analyze: (body: CompilerAnalyzeRequest, signal?: AbortSignal) =>
      request<CompilerAnalyzeResult>('/compiler/analyze', body, signal),
    compilerBenchmark: (body: CompilerBenchmarkRequest, signal?: AbortSignal) =>
      postBenchmark('/api/compiler/benchmark', body, signal),
    optimization: (body: OptimizationRequest, signal?: AbortSignal) =>
      postBenchmark('/api/optimization/run', body, signal),
    search: (body: SearchRequest, signal?: AbortSignal) =>
      postBenchmark('/api/search/run', body, signal),
    materials: (body: MaterialsRequest, signal?: AbortSignal) =>
      postBenchmark('/api/materials/run', body, signal),
    postBenchmark
  };
}

export const api = createApiClient();
