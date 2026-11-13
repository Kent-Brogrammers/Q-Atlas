import type { Experiment, Plan, RecordEntry, Requests, Results, StudyReport } from './model.ts';

export async function runStudy<E extends Experiment>(
  plan: Plan<E>,
  execute: (request: Requests[E], signal: AbortSignal) => Promise<Results[E]>,
  signal: AbortSignal,
  progress: (done: number, total: number) => void = () => {},
  userAgent = ''
): Promise<StudyReport<E>> {
  const report: StudyReport<E> = {
    format_version: 1,
    source: 'live_local_study',
    created_at_utc: new Date().toISOString(),
    status: 'incomplete',
    plan: JSON.parse(JSON.stringify(plan)),
    records: [],
    summary_definition:
      'Per value: median and observed min/max of completed requests, with metric sample counts. No confidence intervals. Raw responses and effective requests retained.',
    provenance: {
      user_agent: userAgent,
      backend_provenance:
        'Package versions and parameters remain in each raw response. Server machine/source revision are not supplied by these endpoints.'
    }
  };
  const deadline = performance.now() + plan.budgetSeconds * 1000;
  for (const point of plan.points) {
    const remaining = deadline - performance.now();
    if (signal.aborted || remaining <= 0) break;
    const controller = new AbortController();
    const abort = () => controller.abort();
    signal.addEventListener('abort', abort, { once: true });
    const timer = setTimeout(abort, remaining);
    const record: RecordEntry<E> = { ...JSON.parse(JSON.stringify(point)), status: 'failed' };
    try {
      record.response = await execute(record.request, controller.signal);
      controller.signal.throwIfAborted();
      if ('status' in record.response && record.response.status !== 'completed')
        throw new Error('Backend did not complete the experiment.');
      record.status = 'completed';
    } catch (error) {
      record.status = controller.signal.aborted ? 'cancelled' : 'failed';
      record.error = controller.signal.aborted
        ? 'Browser request stopped or suite budget expired; backend worker deadlines still apply.'
        : error instanceof Error
          ? error.message
          : 'Request failed.';
      delete record.response;
    } finally {
      clearTimeout(timer);
      signal.removeEventListener('abort', abort);
    }
    report.records.push(record);
    progress(report.records.length, plan.points.length);
    if (record.status !== 'completed') break;
  }
  if (
    report.records.length === plan.points.length &&
    report.records.every((r) => r.status === 'completed')
  )
    report.status = 'completed';
  return report;
}
