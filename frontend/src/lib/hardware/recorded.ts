import raw from '../../../../docs/evidence/ibm-qpu-2026-11-12/five-experiments.json' with { type: 'json' };
import type { HardwareJob } from '../../types/index.ts';
import type { Experiment } from '../studies/model.ts';
import { pickHardwareJob } from './requests.ts';

/** Explicit offline view of measured evidence; never called by a failed live request. */
export function loadPhysicalRecording(experiment: Experiment | 'suite'): HardwareJob {
  const record = JSON.parse(JSON.stringify(raw)) as HardwareJob;
  if (
    record.simulated !== false ||
    record.status !== 'DONE' ||
    !record.measurement_complete ||
    !record.job_id ||
    record.children?.length !== 5 ||
    record.children.some(
      (child) =>
        !child.measurement_complete || !child.counts?.length || child.job_id !== record.job_id
    )
  ) {
    throw new Error('The archived physical evidence is incomplete.');
  }
  return pickHardwareJob(record, experiment);
}
