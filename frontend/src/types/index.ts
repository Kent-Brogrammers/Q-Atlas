import type { components } from './api.generated';

// Generated from the backend OpenAPI document; never hand-edit api.generated.ts.
type Schemas = components['schemas'];
export type QUBO = Schemas['QUBO'];
export type SolverResult = Schemas['SolverResult'];
export type QAOAConfig = Schemas['QAOAConfig'];
export type QAOAResult = Schemas['QAOAResult'];
export type CircuitPreview = Schemas['CircuitPreview'];
export type CircuitGate = Schemas['CircuitGate'];
export type CircuitAngle = Schemas['CircuitAngle'];
export type CompilerAnalyzeRequest = Schemas['CompilerAnalyzeRequest'];
export type CompilerAnalyzeResult = Schemas['CompilerAnalyzeResult'];
export type CompilerGenerateRequest = Schemas['CompilerGenerateRequest'];
export type CompilerGenerateResult = Schemas['CompilerGenerateResult'];
export type GeneratedPythonArtifact = Schemas['GeneratedPythonArtifact'];
export type CompilerBenchmarkRequest = Schemas['CompilerBenchmarkRequest'];
export type CompilerBenchmarkResult = Schemas['CompilerBenchmarkResult'];
export type CompilerBenchmarkPlan = Schemas['CompilerBenchmarkPlan'];
export type OptimizationRequest = Schemas['OptimizationRequest'];
export type OptimizationResult = Schemas['OptimizationResult'];
export type SearchRequest = Schemas['SearchRequest'];
export type SearchResult = Schemas['SearchResult'];
export type MaterialsRequest = Schemas['MaterialsRequest'];
export type MaterialsResult = Schemas['MaterialsResult'];
export type HealthResponse = Schemas['HealthResponse'];
export type ErrorResponse = Schemas['ErrorResponse'];
export type BenchmarkResult =
  CompilerBenchmarkResult | OptimizationResult | SearchResult | MaterialsResult;
