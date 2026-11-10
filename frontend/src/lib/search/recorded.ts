import recordedDemo from './previously-measured.json' with { type: 'json' };
import type { SearchResult } from '../../types/index.ts';
import { curvePoints } from './live.ts';
import { summarizeTrials } from './trials.ts';

export interface RecordingProvenance {
  recorded_at_utc: string;
  source_revision: string;
  recording_method: string;
  working_tree_dirty: boolean;
  source_sha256: Record<string, string>;
  environment: Record<string, string>;
}

interface RecordedBundle extends RecordingProvenance {
  bundle_version: number;
  source: string;
  curve: SearchResult[];
  trials: SearchResult[];
}

export function parseRecordedDemo(value: unknown, mode: 'curve' | 'trials') {
  try {
    const data = value as RecordedBundle;
    if (
      data.bundle_version !== 1 ||
      data.source !== 'previously_measured_search_demo' ||
      data.recording_method !== 'local_fastapi_testclient' ||
      typeof data.source_revision !== 'string' ||
      !data.source_revision ||
      typeof data.working_tree_dirty !== 'boolean' ||
      typeof data.environment?.python !== 'string' ||
      typeof data.environment?.system !== 'string' ||
      !/(Z|[+-]\d{2}:\d{2})$/.test(data.recorded_at_utc) ||
      !Number.isFinite(Date.parse(data.recorded_at_utc)) ||
      !Object.keys(data.source_sha256).length ||
      !Object.values(data.source_sha256).every((hash) => /^[a-f0-9]{64}$/.test(hash))
    ) {
      throw new Error('missing recording provenance');
    }
    if (data.curve.length !== 7 || data.trials.length !== 3)
      throw new Error('incomplete recording');
    for (const [kind, records] of [
      ['curve', data.curve],
      ['trials', data.trials]
    ] as const) {
      curvePoints(records);
      records.forEach((result, index) => {
        const p = result.metadata.parameters;
        const m = result.metrics;
        const iteration = kind === 'curve' ? index : 2;
        const seed = kind === 'curve' ? 42 : 42 + index;
        if (
          result.status !== 'completed' ||
          result.experiment !== 'search' ||
          result.backend !== 'aer_simulator' ||
          result.metadata.simulated !== true ||
          p.num_qubits !== 3 ||
          p.marked_states.join(',') !== '001' ||
          p.iterations !== iteration ||
          result.metadata.seed !== seed ||
          p.config?.seed !== seed ||
          p.config?.shots !== 1024 ||
          m.shots !== 1024 ||
          !Number.isInteger(m.successful_shots) ||
          m.successful_shots! < 0 ||
          m.successful_shots! > 1024 ||
          m.success_probability !== m.successful_shots! / 1024 ||
          m.quantum_oracle_queries !== iteration ||
          m.quantum_total_oracle_queries !== iteration * 1024 ||
          m.classical_observed_queries !== 2 ||
          !result.classical ||
          !result.quantum ||
          !Object.keys(result.metadata.versions ?? {}).length
        ) {
          throw new Error('inconsistent recorded evidence');
        }
      });
    }
    summarizeTrials(data.trials);
    return {
      results: structuredClone(data[mode]),
      provenance: structuredClone({
        recorded_at_utc: data.recorded_at_utc,
        source_revision: data.source_revision,
        recording_method: data.recording_method,
        working_tree_dirty: data.working_tree_dirty,
        source_sha256: data.source_sha256,
        environment: data.environment
      }) satisfies RecordingProvenance
    };
  } catch {
    throw new Error(
      'The previously measured demo is invalid or incomplete. Regenerate it with prepare_search_demo.py.'
    );
  }
}

export function loadRecordedDemo(mode: 'curve' | 'trials') {
  return parseRecordedDemo(recordedDemo, mode);
}

export function buildSearchExport(
  mode: 'single' | 'curve' | 'trials',
  results: SearchResult[],
  recording: RecordingProvenance | null
) {
  const payload = {
    source: recording ? 'previously_measured_search_demo' : 'live_search_api',
    recording,
    mode,
    trial_summary: mode === 'trials' ? summarizeTrials(results) : null,
    results
  };
  // API/export data is JSON. Serialization also unwraps Svelte's reactive proxies,
  // which structuredClone rejects when this helper is called from the live page.
  return JSON.parse(JSON.stringify(payload)) as typeof payload;
}
