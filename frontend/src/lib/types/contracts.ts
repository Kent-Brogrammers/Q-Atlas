/** Shared wire types come from the backend OpenAPI schema, not local copies. */
export type {
  QUBO as Qubo,
  SolverResult,
  BenchmarkResult,
  OptimizationRequest,
  QAOAConfig
} from '../../types/index.ts';
import type { BenchmarkResult } from '../../types/index.ts';
export type Experiment = NonNullable<BenchmarkResult['experiment']>;
