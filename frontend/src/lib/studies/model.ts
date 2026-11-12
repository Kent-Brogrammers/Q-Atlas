import type {
  CompilerBenchmarkRequest,
  CompilerBenchmarkResult,
  MaterialsRequest,
  MaterialsResult,
  NeutrinoRequest,
  NeutrinoResponse,
  OptimizationRequest,
  OptimizationResult,
  SearchRequest,
  SearchResult
} from '../../types/index.ts';

export type Experiment = 'compiler' | 'optimization' | 'materials' | 'search' | 'neutrinos';
export interface Requests {
  compiler: CompilerBenchmarkRequest;
  optimization: OptimizationRequest;
  materials: MaterialsRequest;
  search: SearchRequest;
  neutrinos: NeutrinoRequest;
}
export interface Results {
  compiler: CompilerBenchmarkResult;
  optimization: OptimizationResult;
  materials: MaterialsResult;
  search: SearchResult;
  neutrinos: NeutrinoResponse;
}
export type Axis = 'shots' | 'p' | 'size' | 'trotter_steps' | 'iterations';
export const axes: Record<Experiment, { id: Axis; label: string; values: string }[]> = {
  compiler: [
    { id: 'p', label: 'QAOA layers', values: '1, 2, 3' },
    { id: 'shots', label: 'Final measurement shots', values: '256, 1024, 4096' }
  ],
  optimization: [
    { id: 'size', label: 'Cycle graph vertices', values: '4, 6, 8, 10' },
    { id: 'p', label: 'QAOA layers', values: '1, 2, 3' },
    { id: 'shots', label: 'Final measurement shots', values: '256, 1024, 4096' }
  ],
  materials: [
    { id: 'trotter_steps', label: 'Trotter steps', values: '1, 2, 4, 8, 16, 32' },
    { id: 'shots', label: 'Shots per basis', values: '256, 1024, 4096' }
  ],
  search: [
    { id: 'size', label: 'Search qubits', values: '2, 3, 4, 5, 6' },
    { id: 'iterations', label: 'Grover iterations', values: '0, 1, 2, 3, 4, 5, 6' },
    { id: 'shots', label: 'Shots', values: '256, 1024, 4096' }
  ],
  neutrinos: [{ id: 'shots', label: 'Shots per curve point', values: '256, 1024, 4096' }]
};

export function integers(text: string, label: string, min: number, max: number, limit = 8) {
  const parts = text.split(',').map((value) => value.trim());
  if (!parts.length || parts.length > limit || parts.some((value) => !/^\d+$/.test(value)))
    throw new Error(`${label}: enter 1–${limit} comma-separated integers.`);
  const values = parts.map(Number);
  if (
    new Set(values).size !== values.length ||
    values.some((value) => !Number.isSafeInteger(value) || value < min || value > max)
  )
    throw new Error(`${label}: use distinct integers from ${min} to ${max}.`);
  return values;
}

export function cycleProblem(size: number): OptimizationRequest['problem'] {
  if (!Number.isInteger(size) || size < 3 || size > 16) throw new Error('Cycle size must be 3–16.');
  return {
    kind: 'graph',
    num_vertices: size,
    edges: [
      ...Array.from({ length: size - 1 }, (_, i) => ({ i, j: i + 1, coefficient: 1 })),
      { i: 0, j: size - 1, coefficient: 1 }
    ]
  };
}

export interface Point<E extends Experiment = Experiment> {
  value: number;
  seed: number;
  request: Requests[E];
}
export interface Plan<E extends Experiment = Experiment> {
  experiment: E;
  axis: Axis;
  values: number[];
  seeds: number[];
  points: Point<E>[];
  totalShots: number;
  budgetSeconds: number;
}

// Browser orchestration only: requests keep the established backend contracts.
export function planStudy<E extends Experiment>(
  experiment: E,
  base: Requests[E],
  axis: Axis,
  valueText: string,
  seedText: string,
  budgetSeconds = 120
): Plan<E> {
  if (!axes[experiment].some((item) => item.id === axis))
    throw new Error('Unsupported study axis.');
  const bounds: Record<Axis, [number, number]> = {
    shots: [1, experiment === 'search' ? 10000 : 100000],
    p: [1, 8],
    size: [experiment === 'search' ? 1 : 3, experiment === 'search' ? 6 : 16],
    trotter_steps: [1, 256],
    iterations: [0, 32]
  };
  const values = integers(valueText, 'Values', ...bounds[axis]);
  const seeds = integers(seedText, 'Seeds', 0, 4294967295, 5);
  if (!Number.isFinite(budgetSeconds) || budgetSeconds < 1 || budgetSeconds > 120)
    throw new Error('Study budget must be 1–120 seconds.');
  if (values.length * seeds.length > 24) throw new Error('A study supports at most 24 requests.');
  const points: Point<E>[] = [];
  let totalShots = 0;
  for (const value of values)
    for (const seed of seeds) {
      const request = JSON.parse(JSON.stringify(base)) as Requests[E];
      if (experiment === 'neutrinos') {
        const r = request as NeutrinoRequest;
        r.experiment.shots = value;
        r.experiment.seed = seed;
        const samples = r.samples ?? 21;
        if (samples * value > 500000)
          throw new Error('Neutrino points × shots must be at most 500,000 per request.');
        totalShots += value * samples;
      } else {
        const r = request as Exclude<Requests[Experiment], NeutrinoRequest>;
        r.config = { ...r.config, seed };
        if (axis === 'shots') r.config.shots = value;
        if (axis === 'p')
          (r as OptimizationRequest).config = {
            ...(r as OptimizationRequest).config,
            seed,
            p: value
          };
        if (experiment === 'optimization' && axis === 'size')
          (r as OptimizationRequest).problem = cycleProblem(value);
        if (experiment === 'search' && axis === 'size') {
          // Explicit algorithm demonstration. Do not select late targets to inflate classical time.
          Object.assign(r, {
            num_qubits: value,
            marked_states: ['0'.repeat(value)],
            iterations: null
          });
        }
        if (axis === 'iterations') (r as SearchRequest).iterations = value;
        if (experiment === 'materials') {
          const m = r as MaterialsRequest;
          m.time_samples = 1; // Convergence study at the configured terminal time.
          if (axis === 'trotter_steps') m.trotter_steps = value;
          totalShots += 2 * (m.config?.shots ?? 1024);
        } else totalShots += r.config.shots ?? 1024;
      }
      points.push({ value, seed, request });
    }
  if (totalShots > 2000000) throw new Error('Study measurement budget exceeds 2,000,000 shots.');
  return { experiment, axis, values, seeds, points, totalShots, budgetSeconds };
}

export function median(values: number[]) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}
export type Measurements = Record<string, number | null>;
export function measurements<E extends Experiment>(
  experiment: E,
  response: Results[E]
): Measurements {
  if (experiment === 'neutrinos') {
    const points = (response as NeutrinoResponse).results;
    const sum = (field: 'classical' | 'circuit_end_to_end') =>
      points.every((p) => p.timing_ms[field] != null)
        ? points.reduce((total, p) => total + p.timing_ms[field]!, 0)
        : null;
    return {
      'Classical reference (ms)': sum('classical'),
      'Circuit path (ms)': sum('circuit_end_to_end'),
      'Mean total probability error': points.length
        ? points.reduce((s, p) => s + p.absolute_errors.total.other, 0) / points.length
        : null,
      'Mean sampling error': points.length
        ? points.reduce((s, p) => s + p.absolute_errors.sampling.other, 0) / points.length
        : null
    };
  }
  const result = response as Exclude<Results[Experiment], NeutrinoResponse>;
  const row: Measurements = {
    'Classical reference (ms)': result.classical?.elapsed_ms ?? null,
    'Circuit path (ms)': result.quantum?.elapsed_ms ?? null,
    'Circuit depth': result.metrics.circuit_depth ?? null
  };
  if (experiment === 'materials') {
    const metrics = (result as MaterialsResult).metrics;
    Object.assign(row, {
      'Total observable error': metrics.absolute_error ?? null,
      'Trotter error': metrics.trotter_absolute_error ?? null,
      'Sampling error': metrics.sampling_absolute_error ?? null
    });
  } else if (experiment === 'search') {
    const m = (result as SearchResult).metrics;
    Object.assign(row, {
      'Measured success': m.success_probability ?? null,
      'Ideal success': m.theoretical_success_probability ?? null,
      'Oracle queries per attempt': m.quantum_oracle_queries ?? null,
      'Classical expected queries': m.classical_expected_queries ?? null,
      'Classical observed queries': m.classical_observed_queries ?? null
    });
  } else
    Object.assign(row, {
      'Objective gap': (result as OptimizationResult).metrics.optimality_gap ?? null
    });
  return row;
}

export interface RecordEntry<E extends Experiment = Experiment> extends Point<E> {
  status: 'completed' | 'failed' | 'cancelled';
  response?: Results[E];
  error?: string;
}
export interface StudyReport<E extends Experiment = Experiment> {
  format_version: 1;
  source: 'live_local_study';
  created_at_utc: string;
  status: 'completed' | 'incomplete';
  plan: Plan<E>;
  records: RecordEntry<E>[];
  summary_definition: string;
  provenance: { user_agent: string; backend_provenance: string };
}
export function summarize<E extends Experiment>(report: StudyReport<E>) {
  return report.plan.values.map((value) => {
    const completed = report.records.filter(
      (r) => r.value === value && r.status === 'completed' && r.response
    );
    const rows = completed.map((r) => measurements(report.plan.experiment, r.response!));
    const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    return {
      value,
      count: completed.length,
      metrics: Object.fromEntries(
        keys.map((key) => {
          const values = rows
            .map((row) => row[key])
            .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
          return [
            key,
            {
              count: values.length,
              median: median(values),
              min: values.length ? Math.min(...values) : null,
              max: values.length ? Math.max(...values) : null
            }
          ];
        })
      )
    };
  });
}

export function downloadJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' })
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
