import type {
  OptimizationRequest,
  OptimizationResult,
  QAOAConfig,
  QUBO
} from '../../types/index.ts';
import type { GraphFixture } from '../data/fixtures.ts';

export interface OptimizationSettings {
  layers: number | undefined;
  shots: number | undefined;
  seed: number | undefined;
  maxIterations: number | undefined;
  timeout: number | undefined;
}

export interface OptimizationRun {
  request: OptimizationRequest;
  result: OptimizationResult;
}

export function defaultSettings(): OptimizationSettings {
  return { layers: 2, shots: 1024, seed: 42, maxIterations: 100, timeout: 30 };
}

function integer(value: number | undefined, min: number, max: number, label: string): number {
  if (value === undefined || !Number.isInteger(value) || value < min || value > max) {
    throw new Error(`${label} must be an integer from ${min} to ${max}.`);
  }
  return value;
}

export function buildRequest(
  graph: GraphFixture,
  settings: OptimizationSettings
): OptimizationRequest {
  if (
    settings.timeout === undefined ||
    !Number.isFinite(settings.timeout) ||
    settings.timeout <= 0 ||
    settings.timeout > 60
  ) {
    throw new Error('Each solver timeout must be greater than zero and at most 60 seconds.');
  }
  return {
    problem: {
      kind: 'graph',
      num_vertices: graph.nodes.length,
      edges: graph.edges.map(([i, j]) => ({ i, j, coefficient: 1 }))
    },
    config: {
      backend: 'aer_simulator',
      optimizer: 'COBYLA',
      p: integer(settings.layers, 1, 8, 'QAOA layers'),
      shots: integer(settings.shots, 1, 100000, 'Shots'),
      seed: integer(settings.seed, 0, 2 ** 32 - 1, 'Seed'),
      max_iterations: integer(settings.maxIterations, 1, 1000, 'Optimizer evaluations'),
      timeout_seconds: settings.timeout
    }
  };
}

export type OptimizationCall = (
  request: OptimizationRequest,
  signal?: AbortSignal
) => Promise<OptimizationResult>;

export async function measureOptimization(
  graph: GraphFixture,
  settings: OptimizationSettings,
  optimization: OptimizationCall,
  signal: AbortSignal
): Promise<OptimizationRun> {
  const request = buildRequest(graph, settings);
  signal.throwIfAborted();
  const result = await optimization(request, signal);
  signal.throwIfAborted();
  const qubo = result?.metadata?.qubo;
  const pairs = (value: QUBO) =>
    (value.quadratic ?? []).map(({ i, j, coefficient }) => [i, j, coefficient]);
  if (
    result?.status !== 'completed' ||
    result.experiment !== 'optimization' ||
    result.backend !== 'aer_simulator' ||
    !qubo ||
    qubo.num_variables !== graph.nodes.length ||
    (qubo.constant ?? 0) !== graph.qubo.constant ||
    JSON.stringify(qubo.linear) !== JSON.stringify(graph.qubo.linear) ||
    JSON.stringify(pairs(qubo)) !== JSON.stringify(pairs(graph.qubo))
  ) {
    throw new Error('The backend returned a different optimization problem.');
  }
  if (
    result.metadata.seed !== request.config?.seed ||
    Object.entries(request.config ?? {}).some(
      ([key, value]) => result.metadata.config?.[key as keyof QAOAConfig] !== value
    )
  ) {
    throw new Error('The backend returned different solver settings.');
  }
  for (const solver of [result.classical, result.quantum]) {
    const bits = solver?.best_bitstring;
    if (bits != null && (bits.length !== graph.nodes.length || !/^[01]+$/.test(bits))) {
      throw new Error('The backend returned an invalid x[0]-first assignment.');
    }
    if (
      solver &&
      ((solver.objective != null && !Number.isFinite(solver.objective)) ||
        !Number.isFinite(solver.elapsed_ms) ||
        solver.elapsed_ms < 0)
    ) {
      throw new Error('The backend returned an invalid objective or duration.');
    }
  }
  return { request, result };
}

export function buildMeasuredExport(run: OptimizationRun) {
  return JSON.parse(JSON.stringify({ source: 'live_local_simulator', ...run })) as {
    source: 'live_local_simulator';
    request: OptimizationRequest;
    result: OptimizationResult;
  };
}

export function milliseconds(value: number | null | undefined): string {
  return value == null ? 'Not measured' : `${value.toFixed(3)} ms`;
}
