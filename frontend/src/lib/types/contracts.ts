/** Mirrors project spec §6.1; backend validation/normalization remains authoritative. */
export interface Qubo {
  num_variables: number;
  constant: number;
  linear: number[];
  quadratic: { i: number; j: number; coefficient: number }[];
  sense: 'minimize';
}

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type JsonObject = { [key: string]: Json };
export type Experiment = 'compiler' | 'materials' | 'optimization' | 'search';

/** Only the documented result fields are fixed; experiment-specific metrics stay extensible. */
export interface SolverResult {
  algorithm: string;
  elapsed_ms: number | null;
  objective: number | null;
}

export interface BenchmarkResult {
  experiment: Experiment;
  problem_id: string;
  backend: string;
  classical: SolverResult | null;
  quantum: SolverResult | null;
  metrics: JsonObject;
  metadata: JsonObject;
}

export type BenchmarkEndpoint =
  '/api/compiler/benchmark' | '/api/optimization/run' | '/api/materials/run' | '/api/search/run';
