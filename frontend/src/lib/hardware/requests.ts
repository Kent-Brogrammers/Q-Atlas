import type {
  HardwareRequest,
  HardwareJob,
  CompilerBenchmarkRequest,
  MaterialsRequest,
  NeutrinoRequest,
  OptimizationRequest
} from '../../types/index.ts';
import type { Experiment, Requests } from '../studies/model.ts';

export function hardwareTask(
  experiment: Experiment,
  base: Requests[Experiment],
  shots: number,
  points: number,
  steps: number,
  layers: number
): HardwareRequest['task'] {
  if (!Number.isInteger(shots) || shots < 1 || shots > 128)
    throw new Error('QPU shots must be 1–128.');
  if (!Number.isInteger(points) || points < 1 || points > 5)
    throw new Error('QPU curve points must be 1–5.');
  if (!Number.isInteger(steps) || steps < 1 || steps > 32)
    throw new Error('QPU Trotter steps must be 1–32.');
  if (!Number.isInteger(layers) || layers < 1 || layers > 2)
    throw new Error('QPU layers must be 1–2.');
  if (experiment === 'optimization') {
    const p = (base as OptimizationRequest).problem;
    if ((p.kind === 'graph' ? p.num_vertices : p.qubo.num_variables) > 8)
      throw new Error(
        'This larger benchmark runs locally. Choose a graph with at most 8 choices for a physical QPU run.'
      );
  }
  const parameters = JSON.parse(JSON.stringify(base)) as Requests[Experiment];
  if (experiment === 'neutrinos') {
    const p = parameters as NeutrinoRequest;
    p.samples = Math.max(2, points);
    p.experiment.shots = shots;
  } else {
    const p = parameters as Exclude<Requests[Experiment], NeutrinoRequest>;
    p.config = { ...p.config, shots };
    if (experiment === 'materials')
      Object.assign(p as MaterialsRequest, { time_samples: points, trotter_steps: steps });
    if (experiment === 'compiler' || experiment === 'optimization') {
      const q = p as CompilerBenchmarkRequest | OptimizationRequest;
      q.config = { ...q.config, p: layers, max_iterations: 20, timeout_seconds: 30 };
    }
  }
  // Backend discriminated schemas validate every mathematical request again.
  return { kind: experiment, parameters } as HardwareRequest['task'];
}

export function canStartAnother(job: HardwareJob | null) {
  return (
    !job ||
    job.measurement_complete ||
    ['CANCELLED', 'ERROR', 'FAILED_BEFORE_SUBMISSION'].includes(job.status)
  );
}

export function canSubmit(job: HardwareJob | null, pendingId: string) {
  return !pendingId || (!!job && job.request_id === pendingId && canStartAnother(job));
}

export function makeRequest(
  task: HardwareRequest['task'],
  id: string,
  backend: string,
  shotOverride?: number
): HardwareRequest {
  const shots =
    shotOverride ??
    (task.kind === 'suite'
      ? 128
      : task.kind === 'neutrinos'
        ? task.parameters.experiment.shots
        : task.parameters.config?.shots);
  return {
    task,
    request_id: id,
    confirmed: true,
    backend_name: backend || null,
    shots: shots ?? 128,
    max_execution_seconds: 10
  };
}

export function pickHardwareJob(job: HardwareJob, experiment: Experiment | 'suite'): HardwareJob {
  return job.task.kind === 'suite' && experiment !== 'suite'
    ? (job.children?.find((child) => child.task.kind === experiment) ?? job)
    : job;
}
