<script lang="ts">
  import { onDestroy } from 'svelte';
  import { api, ApiError } from '../../api/client.ts';
  import type {
    CompilerBenchmarkRequest,
    CompilerBenchmarkResult,
    OptimizationRequest,
    OptimizationResult
  } from '../../types/index.ts';
  import { downloadJson } from '../studies/model.ts';
  import ComparisonResult from './ComparisonResult.svelte';
  import StudyPanel from './StudyPanel.svelte';
  import Panel from './Panel.svelte';
  import HardwarePanel from './HardwarePanel.svelte';
  let {
    source,
    problem,
    onResult
  }: {
    source?: string;
    problem?: OptimizationRequest['problem'];
    onResult?: (result: CompilerBenchmarkResult | OptimizationResult | null) => void;
  } = $props();
  let layers = $state(1);
  let shots = $state(1024);
  let seed = $state(42);
  let evaluations = $state(20);
  let timeout = $state(30);
  let running = $state(false);
  let studying = $state(false);
  let result = $state<CompilerBenchmarkResult | OptimizationResult | null>(null);
  let error = $state('');
  let controller: AbortController | undefined;
  let revision = 0;
  let experiment = $derived(
    source === undefined ? ('optimization' as const) : ('compiler' as const)
  );
  let request = $derived.by(() => {
    if (
      ![layers, shots, seed, evaluations, timeout].every(Number.isInteger) ||
      layers < 1 ||
      layers > 8 ||
      shots < 1 ||
      shots > 100000 ||
      seed < 0 ||
      seed > 4294967295 ||
      evaluations < 1 ||
      evaluations > 1000 ||
      timeout < 1 ||
      timeout > 60
    )
      return null;
    const config = {
      p: layers,
      shots,
      seed,
      max_iterations: evaluations,
      timeout_seconds: timeout,
      optimizer: 'COBYLA' as const
    };
    return source === undefined ? (problem ? { problem, config } : null) : { source, config };
  });
  let key = $derived(JSON.stringify(request));
  $effect(() => {
    key;
    revision++;
    controller?.abort();
    result = null;
    onResult?.(null);
    error = '';
  });
  onDestroy(() => {
    revision++;
    controller?.abort();
  });
  async function run() {
    if (running || studying || !request) return;
    const version = revision;
    running = true;
    result = null;
    error = '';
    controller = new AbortController();
    try {
      const measured =
        source === undefined
          ? await api.optimization(request as OptimizationRequest, controller.signal)
          : await api.compilerBenchmark(request as CompilerBenchmarkRequest, controller.signal);
      controller.signal.throwIfAborted();
      if (version === revision) {
        result = measured;
        onResult?.(measured);
      }
    } catch (cause) {
      if (version === revision)
        error =
          cause instanceof ApiError && cause.status === 501 && source !== undefined
            ? 'Local compiler execution is disabled. Start the backend with QATLAS_ENABLE_COMPILER_AER=1, or use ./dev.sh which enables local comparisons.'
            : cause instanceof ApiError
              ? [
                  cause.message,
                  ...(cause.body.error.diagnostics ?? []).map((item) => item.message)
                ].join(' ')
              : cause instanceof Error
                ? cause.message
                : 'Comparison failed.';
    } finally {
      running = false;
    }
  }
</script>

<HardwarePanel {experiment} {request} />

<Panel title="Run a local comparison" subtitle="Exact classical solve and shared QAOA · Qiskit Aer">
  <div class="workspace-body">
    <p>Choose the same objective and a bounded solver budget. No IBM account is required.</p>
    <form
      onsubmit={(event) => {
        event.preventDefault();
        void run();
      }}
    >
      <fieldset disabled={running || studying}>
        <label
          >QAOA layers<input type="number" min="1" max="8" required bind:value={layers} /></label
        >
        <label
          >Final shots<input
            type="number"
            min="1"
            max="100000"
            required
            bind:value={shots}
          /></label
        >
        <label
          >Seed<input type="number" min="0" max="4294967295" required bind:value={seed} /></label
        >
        <label
          >Optimizer evaluation budget<input
            type="number"
            min="1"
            max="1000"
            required
            bind:value={evaluations}
          /></label
        >
        <label
          >Timeout per solver (seconds)<input
            type="number"
            min="1"
            max="60"
            required
            bind:value={timeout}
          /></label
        >
      </fieldset>
      <div class="actions">
        <button class="button primary" disabled={running || studying || !request}
          >{running ? 'Running comparison…' : 'Run local comparison'}</button
        >
        {#if running}<button type="button" class="button" onclick={() => controller?.abort()}
            >Stop waiting</button
          >{/if}
        {#if result}<button
            type="button"
            class="button"
            onclick={() =>
              downloadJson(
                { source: 'live_local_comparison', request, result },
                `q-atlas-${experiment}-comparison.json`
              )}>Download result JSON</button
          >{/if}
      </div>
    </form>
    {#if !request}<p role="alert">Enter valid settings before running.</p>{/if}
    {#if error}<p role="alert">{error}</p>{/if}
    {#if running}<p role="status">
        Solvers run sequentially. Stopping browser waiting leaves backend worker deadlines in force.
      </p>{/if}
    {#if result}<ComparisonResult {result} />{/if}
  </div>
</Panel>
<StudyPanel {experiment} {request} disabled={running || studying} />

<style>
  .workspace-body {
    padding: 0 22px 22px;
  }
  p {
    font-size: 13px;
    line-height: 1.7;
  }
  fieldset {
    border: 0;
    margin: 0 0 18px;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 14px;
  }
  label {
    display: grid;
    gap: 8px;
    color: var(--muted);
    font-size: 12px;
  }
  input {
    min-width: 0;
    width: 100%;
    padding: 9px;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
</style>
