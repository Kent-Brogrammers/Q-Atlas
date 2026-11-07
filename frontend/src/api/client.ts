import type {
  CompilerAnalyzeRequest, CompilerAnalyzeResult, CompilerBenchmarkRequest, CompilerBenchmarkResult,
  ErrorResponse, HealthResponse, MaterialsRequest, MaterialsResult,
  OptimizationRequest, OptimizationResult, SearchRequest, SearchResult,
} from '../types';

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly body: ErrorResponse) {
    super(body.error.message);
  }
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(65_000),
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    if (typeof payload === 'object' && payload !== null && 'error' in payload) {
      throw new ApiError(response.status, payload as ErrorResponse);
    }
    throw new Error(`API request failed (HTTP ${response.status}).`);
  }
  return payload as T;
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  analyze: (body: CompilerAnalyzeRequest) => request<CompilerAnalyzeResult>('/compiler/analyze', body),
  compilerBenchmark: (body: CompilerBenchmarkRequest) => request<CompilerBenchmarkResult>('/compiler/benchmark', body),
  optimization: (body: OptimizationRequest) => request<OptimizationResult>('/optimization/run', body),
  search: (body: SearchRequest) => request<SearchResult>('/search/run', body),
  materials: (body: MaterialsRequest) => request<MaterialsResult>('/materials/run', body),
};
