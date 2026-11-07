/** Presentation-only values. These are not backend responses or measured runs. */
export interface ExampleComparison {
  kind: 'ui_example';
  problem_id: string;
  classical: { algorithm: string; elapsed_ms: null; objective: number };
  quantum: { algorithm: 'qaoa'; elapsed_ms: null; objective: number };
  metrics: {
    num_qubits: null;
    circuit_depth: null;
    shots: null;
    optimizer_evaluations: null;
  };
}
