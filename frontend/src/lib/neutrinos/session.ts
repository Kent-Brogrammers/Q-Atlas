import { buildRequest, defaultSettings, type Environment, type LabSettings } from './live.ts';
import type { NeutrinoRequest, NeutrinoResponse } from '../../types/index.ts';

export function preset(environment: Environment): LabSettings {
  const base = defaultSettings();
  if (environment === 'density') return { ...base, environment, distance: 4.0336988686318564 };
  if (environment === 'layers') return { ...base, environment, distance: 2, potential: 0.2 };
  return { ...base, environment };
}
export type RunState =
  | { status: 'waiting' | 'running' }
  | { status: 'error'; message: string }
  | { status: 'ready'; request: NeutrinoRequest; result: NeutrinoResponse };

// A server worker may keep running after a fetch is cancelled. Serialize runs and
// retain only the latest queued configuration while one is in flight.
export function createLabRunner(
  execute: (request: NeutrinoRequest, signal: AbortSignal) => Promise<NeutrinoResponse>,
  publish: (state: RunState) => void
) {
  let revision = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let queued: NeutrinoRequest | undefined;
  let active: AbortController | undefined;
  let last: { key: string; result: NeutrinoResponse } | undefined;
  async function drain() {
    if (active || !queued) return;
    const request = queued;
    queued = undefined;
    const id = revision;
    const key = JSON.stringify(request);
    if (last?.key === key) {
      publish({ status: 'ready', request, result: last.result });
      return;
    }
    active = new AbortController();
    publish({ status: 'running' });
    try {
      const result = await execute(request, active.signal);
      if (id === revision) {
        last = { key, result };
        publish({ status: 'ready', request, result });
      }
    } catch (cause) {
      if (id === revision)
        publish({
          status: 'error',
          message: cause instanceof Error ? cause.message : 'Simulation failed.'
        });
    } finally {
      active = undefined;
      void drain();
    }
  }
  return {
    update(settings: LabSettings, delay = 550) {
      revision++;
      clearTimeout(timer);
      queued = undefined;
      try {
        const request = buildRequest(settings);
        publish({ status: 'waiting' });
        timer = setTimeout(() => {
          queued = request;
          void drain();
        }, delay);
      } catch (cause) {
        publish({
          status: 'error',
          message: String(cause instanceof Error ? cause.message : cause)
        });
      }
    },
    dispose() {
      revision++;
      queued = undefined;
      clearTimeout(timer);
      active?.abort();
    }
  };
}
