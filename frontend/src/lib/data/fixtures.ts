import type { BenchmarkResult, Qubo } from '../types/contracts.ts';

export interface GraphFixture {
  id: string;
  name: string;
  description: string;
  nodes: { x: number; y: number }[];
  edges: [number, number][];
  assignment: number[];
  optimumCut: number;
  qubo: Qubo;
}

// Hand-authored UI examples. No graph generator, optimizer, or quantum execution is used.
export const graphs: GraphFixture[] = [
  {
    id: 'prism',
    name: 'Triangular prism',
    description: 'Two triangles, three connecting edges.',
    nodes: [
      { x: 180, y: 85 },
      { x: 405, y: 85 },
      { x: 490, y: 230 },
      { x: 405, y: 365 },
      { x: 180, y: 365 },
      { x: 95, y: 230 }
    ],
    edges: [
      [0, 2],
      [2, 4],
      [0, 4],
      [1, 3],
      [3, 5],
      [1, 5],
      [0, 1],
      [2, 3],
      [4, 5]
    ],
    assignment: [0, 1, 1, 0, 1, 0],
    optimumCut: 7,
    qubo: {
      num_variables: 6,
      constant: 0,
      linear: [-3, -3, -3, -3, -3, -3],
      quadratic: [
        { i: 0, j: 1, coefficient: 2 },
        { i: 0, j: 2, coefficient: 2 },
        { i: 0, j: 4, coefficient: 2 },
        { i: 1, j: 3, coefficient: 2 },
        { i: 1, j: 5, coefficient: 2 },
        { i: 2, j: 3, coefficient: 2 },
        { i: 2, j: 4, coefficient: 2 },
        { i: 3, j: 5, coefficient: 2 },
        { i: 4, j: 5, coefficient: 2 }
      ],
      sense: 'minimize'
    }
  },
  {
    id: 'cube',
    name: 'Cube graph',
    description: 'Eight vertices on a bipartite cube.',
    nodes: [
      { x: 160, y: 80 },
      { x: 380, y: 80 },
      { x: 380, y: 300 },
      { x: 160, y: 300 },
      { x: 250, y: 150 },
      { x: 470, y: 150 },
      { x: 470, y: 370 },
      { x: 250, y: 370 }
    ],
    edges: [
      [0, 1],
      [1, 2],
      [2, 3],
      [0, 3],
      [4, 5],
      [5, 6],
      [6, 7],
      [4, 7],
      [0, 4],
      [1, 5],
      [2, 6],
      [3, 7]
    ],
    assignment: [0, 1, 0, 1, 1, 0, 1, 0],
    optimumCut: 12,
    qubo: {
      num_variables: 8,
      constant: 0,
      linear: [-3, -3, -3, -3, -3, -3, -3, -3],
      quadratic: [
        { i: 0, j: 1, coefficient: 2 },
        { i: 0, j: 3, coefficient: 2 },
        { i: 0, j: 4, coefficient: 2 },
        { i: 1, j: 2, coefficient: 2 },
        { i: 1, j: 5, coefficient: 2 },
        { i: 2, j: 3, coefficient: 2 },
        { i: 2, j: 6, coefficient: 2 },
        { i: 3, j: 7, coefficient: 2 },
        { i: 4, j: 5, coefficient: 2 },
        { i: 4, j: 7, coefficient: 2 },
        { i: 5, j: 6, coefficient: 2 },
        { i: 6, j: 7, coefficient: 2 }
      ],
      sense: 'minimize'
    }
  },
  {
    id: 'cycle',
    name: 'Four-node cycle',
    description: 'A small reference instance with four edges.',
    nodes: [
      { x: 190, y: 100 },
      { x: 430, y: 100 },
      { x: 430, y: 340 },
      { x: 190, y: 340 }
    ],
    edges: [
      [0, 1],
      [1, 2],
      [2, 3],
      [0, 3]
    ],
    assignment: [0, 1, 0, 1],
    optimumCut: 4,
    qubo: {
      num_variables: 4,
      constant: 0,
      linear: [-2, -2, -2, -2],
      quadratic: [
        { i: 0, j: 1, coefficient: 2 },
        { i: 0, j: 3, coefficient: 2 },
        { i: 1, j: 2, coefficient: 2 },
        { i: 2, j: 3, coefficient: 2 }
      ],
      sense: 'minimize'
    }
  }
];

export interface ExampleRun {
  benchmark: BenchmarkResult;
  expected: number[];
  bestSampled: number[];
  histogram: { cut: number; count: number }[];
  fixtureConfig: { p: number; shots: number; seed: number; optimizer: string };
}

export const exampleRuns: Record<string, ExampleRun> = {
  prism: {
    benchmark: {
      experiment: 'optimization',
      problem_id: 'ui-example-prism',
      backend: 'aer_simulator',
      classical: { algorithm: 'brute_force', elapsed_ms: 0.43, objective: -7 },
      quantum: { algorithm: 'qaoa', elapsed_ms: 1284, objective: -7 },
      metrics: { num_qubits: 6, circuit_depth: 38, shots: 1024, optimizer_evaluations: 32 },
      metadata: {
        seed: 42,
        timing_scope: 'illustrative_fixture',
        simulated: true,
        ui_fixture: true
      }
    },
    expected: [
      -3.15, -3.62, -3.45, -4.1, -4.48, -4.32, -4.9, -5.0, -4.97, -5.15, -5.3, -5.32, -5.34, -5.38,
      -5.4, -5.40625
    ],
    bestSampled: [-3, -4, -4, -5, -5, -5, -6, -6, -6, -6, -7, -7, -7, -7, -7, -7],
    histogram: [
      { cut: 7, count: 316 },
      { cut: 6, count: 256 },
      { cut: 5, count: 200 },
      { cut: 4, count: 128 },
      { cut: 3, count: 92 },
      { cut: 0, count: 32 }
    ],
    fixtureConfig: { p: 2, shots: 1024, seed: 42, optimizer: 'COBYLA' }
  },
  cube: {
    benchmark: {
      experiment: 'optimization',
      problem_id: 'ui-example-cube',
      backend: 'aer_simulator',
      classical: { algorithm: 'brute_force', elapsed_ms: 0.87, objective: -12 },
      quantum: { algorithm: 'qaoa', elapsed_ms: 1862, objective: -12 },
      metrics: { num_qubits: 8, circuit_depth: 46, shots: 1024, optimizer_evaluations: 32 },
      metadata: {
        seed: 42,
        timing_scope: 'illustrative_fixture',
        simulated: true,
        ui_fixture: true
      }
    },
    expected: [
      -5.1, -5.8, -5.65, -6.75, -7.3, -7.1, -8.4, -8.8, -8.62, -9.0, -9.2, -9.35, -9.48, -9.56,
      -9.6, -9.63671875
    ],
    bestSampled: [-6, -6, -8, -8, -8, -8, -9, -9, -9, -9, -9, -12, -12, -12, -12, -12],
    histogram: [
      { cut: 12, count: 420 },
      { cut: 9, count: 292 },
      { cut: 8, count: 196 },
      { cut: 6, count: 84 },
      { cut: 4, count: 32 }
    ],
    fixtureConfig: { p: 2, shots: 1024, seed: 42, optimizer: 'COBYLA' }
  },
  cycle: {
    benchmark: {
      experiment: 'optimization',
      problem_id: 'ui-example-cycle',
      backend: 'aer_simulator',
      classical: { algorithm: 'brute_force', elapsed_ms: 0.12, objective: -4 },
      quantum: { algorithm: 'qaoa', elapsed_ms: 726, objective: -4 },
      metrics: { num_qubits: 4, circuit_depth: 22, shots: 1024, optimizer_evaluations: 32 },
      metadata: {
        seed: 42,
        timing_scope: 'illustrative_fixture',
        simulated: true,
        ui_fixture: true
      }
    },
    expected: [
      -1.8, -2.1, -2.05, -2.4, -2.65, -2.55, -2.9, -3.0, -2.95, -3.1, -3.15, -3.2, -3.23, -3.27,
      -3.3, -3.3125
    ],
    bestSampled: [-2, -2, -2, -2, -4, -4, -4, -4, -4, -4, -4, -4, -4, -4, -4, -4],
    histogram: [
      { cut: 4, count: 704 },
      { cut: 2, count: 288 },
      { cut: 0, count: 32 }
    ],
    fixtureConfig: { p: 2, shots: 1024, seed: 42, optimizer: 'COBYLA' }
  }
};

export function getExampleRun(id: string): ExampleRun {
  const fixture = exampleRuns[id];
  if (!fixture) throw new Error(`No UI example exists for graph '${id}'.`);
  return structuredClone(fixture);
}
