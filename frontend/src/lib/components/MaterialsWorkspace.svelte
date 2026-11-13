<script lang="ts">
  import { duration } from '../presentation/format.ts';
  import { onDestroy } from 'svelte';
  import StudyPanel from './StudyPanel.svelte';
  import ExecutionChoice from './ExecutionChoice.svelte';
  import { downloadJson } from '../studies/model.ts';
  import { api, ApiError } from '../../api/client.ts';
  import type { MaterialsRequest, MaterialsResult } from '../../types/index.ts';
  import Icon from './Icon.svelte';
  import Metric from './Metric.svelte';
  import Panel from './Panel.svelte';
  import MaterialsTimeSeriesChart from './MaterialsTimeSeriesChart.svelte';

  let spins = $state(3);
  let coupling = $state(1);
  let field = $state(0.7);
  let observable = $state<'energy' | 'magnetization'>('magnetization');
  let evolutionTime = $state(1);
  let trotterSteps = $state(32);
  let timeSamples = $state(5);
  let shots = $state(512);
  let seed = $state(42);
  let timeoutSeconds = $state(30);
  let running = $state(false);
  let studying = $state(false);
  let result = $state<MaterialsResult | null>(null);
  let errorMessage = $state('');
  let requestController: AbortController | null = null;

  let requestIssue = $derived.by(() => {
    if (!Number.isInteger(spins) || spins < 2 || spins > 4) {
      return 'Spin count must be an integer from 2 to 4.';
    }
    if (!Number.isFinite(coupling) || Math.abs(coupling) > 10) {
      return 'Coupling must be finite and within [-10, 10].';
    }
    if (!Number.isFinite(field) || Math.abs(field) > 10) {
      return 'Transverse field must be finite and within [-10, 10].';
    }
    if (!Number.isFinite(evolutionTime) || evolutionTime < 0 || evolutionTime > 10) {
      return 'Terminal time must be finite and within [0, 10].';
    }
    if (!Number.isInteger(trotterSteps) || trotterSteps < 1 || trotterSteps > 256) {
      return 'Trotter steps must be an integer from 1 to 256.';
    }
    if (!Number.isInteger(timeSamples) || timeSamples < 1 || timeSamples > 21) {
      return 'Time samples must be an integer from 1 to 21.';
    }
    if (!Number.isInteger(shots) || shots < 1 || shots > 100_000) {
      return 'Shots per basis must be an integer from 1 to 100,000.';
    }
    if (!Number.isInteger(seed) || seed < 0 || seed > 4_294_967_295) {
      return 'Seed must be an unsigned 32-bit integer.';
    }
    if (!Number.isInteger(timeoutSeconds) || timeoutSeconds < 1 || timeoutSeconds > 60) {
      return 'Timeout must be an integer from 1 to 60 seconds.';
    }
    if (timeSamples * trotterSteps > 2048) {
      return 'Time samples multiplied by Trotter steps must not exceed 2,048.';
    }
    if (2 * timeSamples * shots > 1_000_000) {
      return 'Two measurement bases multiplied by time samples and shots must not exceed 1,000,000.';
    }
    if (timeSamples > 1 && evolutionTime === 0) {
      return 'A time sweep needs a positive terminal evolution time.';
    }
    return '';
  });

  let selectedUnit = $derived(
    result
      ? observable === 'energy'
        ? result.metadata.energy_unit
        : result.metadata.observable_unit
      : observable === 'energy'
        ? 'dimensionless energy'
        : 'per spin'
  );
  let selectedLabel = $derived(observable === 'energy' ? 'Total energy' : 'Z magnetization');

  function formatValue(value: number | null | undefined, digits = 4) {
    return value == null ? 'Not reported' : value.toFixed(digits);
  }

  function describeError(error: unknown) {
    if (error instanceof ApiError) {
      const diagnostics = (error.body.error.diagnostics ?? [])
        .map((item) => `${item.line ? `Line ${item.line}: ` : ''}${item.message}`)
        .join(' ');
      return `${error.body.error.code}: ${error.body.error.message}${diagnostics ? ` ${diagnostics}` : ''}`;
    }
    return error instanceof Error ? error.message : 'The materials request failed.';
  }

  let currentRequest = $derived.by(() => {
    if (requestIssue) return null;
    return {
      model: 'ising',
      num_spins: spins,
      coupling,
      field,
      boundary: 'open',
      observable,
      evolution_time: evolutionTime,
      trotter_steps: trotterSteps,
      time_samples: timeSamples,
      config: {
        backend: 'aer_simulator',
        shots,
        seed,
        timeout_seconds: timeoutSeconds
      }
    } satisfies MaterialsRequest;
  });
  $effect(() => {
    currentRequest;
    result = null;
    errorMessage = '';
  });

  async function runSimulation() {
    if (running || studying || requestIssue) return;

    const request = currentRequest;
    if (!request) return;

    result = null;
    errorMessage = '';
    running = true;
    const controller = new AbortController();
    requestController = controller;

    try {
      result = await api.materials(request, controller.signal);
    } catch (error: unknown) {
      errorMessage = describeError(error);
    } finally {
      if (requestController === controller) {
        requestController = null;
        running = false;
      }
    }
  }

  function cancelRequest() {
    requestController?.abort();
  }

  onDestroy(cancelRequest);
</script>

<svelte:head>
  <title>Quantum Materials · Q-Atlas</title>
</svelte:head>

<header class="page-heading">
  <div>
    <p class="eyebrow">Spin Hamiltonian · exact reference</p>
    <h1>Quantum Materials</h1>
    <p>
      Simulate real-time dynamics of a small transverse-field Ising chain and compare the shot-based
      circuit output with an independent classical reference.
    </p>
  </div>
</header>

<div class="provenance-note">
  <Icon name="info" size={15} />
  <strong>Local simulation or physical QPU</strong>
  <span>Use the local controls below for Aer, or expand Physical QPU for IBM measurements.</span>
</div>

<ExecutionChoice experiment="materials" request={currentRequest}>
  <div class="materials-grid">
    <Panel
      title="Model and run settings"
      subtitle="Dimensionless units with ℏ = 1; open Ising chain."
    >
      <form
        class="settings-form"
        onsubmit={(event) => {
          event.preventDefault();
          void runSimulation();
        }}
      >
        <fieldset disabled={running || studying}>
          <details>
            <summary>Change model &amp; sampling settings</summary>
            <div class="control-grid">
              <label for="spin-count">Spins</label>
              <select id="spin-count" bind:value={spins}>
                <option value={2}>2 spins</option>
                <option value={3}>3 spins</option>
                <option value={4}>4 spins</option>
              </select>

              <label for="coupling">Coupling J</label>
              <input
                id="coupling"
                type="number"
                min="-10"
                max="10"
                step="0.1"
                required
                bind:value={coupling}
              />

              <label for="field">Transverse field h</label>
              <input
                id="field"
                type="number"
                min="-10"
                max="10"
                step="0.1"
                required
                bind:value={field}
              />

              <label for="observable">Reported observable</label>
              <select id="observable" bind:value={observable}>
                <option value="magnetization">Mean Z magnetization</option>
                <option value="energy">Total energy</option>
              </select>

              <label for="evolution-time">Terminal time</label>
              <input
                id="evolution-time"
                type="number"
                min="0"
                max="10"
                step="0.1"
                required
                bind:value={evolutionTime}
              />

              <label for="trotter-steps">Trotter steps</label>
              <input
                id="trotter-steps"
                type="number"
                min="1"
                max="256"
                step="1"
                required
                bind:value={trotterSteps}
              />

              <label for="time-samples">Time samples</label>
              <input
                id="time-samples"
                type="number"
                min="1"
                max="21"
                step="1"
                required
                bind:value={timeSamples}
              />

              <label for="shot-count">Shots per basis and time</label>
              <input
                id="shot-count"
                type="number"
                min="1"
                max="100000"
                step="1"
                required
                bind:value={shots}
              />

              <label for="seed">Random seed</label>
              <input
                id="seed"
                type="number"
                min="0"
                max="4294967295"
                step="1"
                required
                bind:value={seed}
              />

              <label for="timeout">Timeout</label>
              <input
                id="timeout"
                type="number"
                min="1"
                max="60"
                step="1"
                required
                bind:value={timeoutSeconds}
              />
            </div>
            <p class="field-help">
              Each time point starts from |00…0⟩. A time sweep must have a positive terminal time.
              Work is limited to 2,048 sample-step pairs and 1,000,000 total basis shots.
            </p>
          </details>
          {#if requestIssue}
            <p class="request-issue" role="status">{requestIssue}</p>
          {/if}
          <button
            class="button primary run-button"
            type="submit"
            disabled={running || !!requestIssue}
          >
            {#if running}
              <span>Running simulation…</span>
            {:else}
              <span>Run comparison</span><Icon name="arrow" size={16} />
            {/if}
          </button>
        </fieldset>
        {#if running}
          <button class="button quiet cancel-button" type="button" onclick={cancelRequest}>
            Cancel request
          </button>
        {/if}
      </form>
    </Panel>

    <Panel
      title="Simulation results"
      subtitle="Results appear only after a successful response from the live materials endpoint."
    >
      {#if running}
        <p class="run-status" role="status" aria-live="polite">
          The backend is calculating the exact reference and Aer circuit results. This may take a
          moment.
        </p>
      {:else if errorMessage}
        <div class="error-state" role="alert">
          <strong>Simulation failed</strong>
          <p>{errorMessage}</p>
          <p>No example or cached result was substituted.</p>
        </div>
      {:else if result}
        <div class="result-content">
          <div class="result-provenance">
            <span class="backend-badge">{result.backend}</span>
            <span>Simulated · {result.metadata.simulation_method}</span>
            <span>Timing: {result.metadata.timing_scope}</span>
          </div>
          <div class="metrics-grid">
            <Metric
              label={`Exact ${selectedLabel}`}
              value={formatValue(result.metrics.classical_observable)}
              unit={selectedUnit}
              note={result.classical?.algorithm ?? 'Independent classical reference'}
            />
            <Metric
              label={`Shot-based ${selectedLabel}`}
              value={formatValue(result.metrics.quantum_observable)}
              unit={selectedUnit}
              note={result.quantum?.algorithm ?? 'Aer circuit simulation'}
              tone="violet"
            />
            <Metric
              label="Absolute error"
              value={formatValue(result.metrics.absolute_error)}
              note="Shot-based circuit vs. exact reference"
              tone="cyan"
            />
            <Metric
              label="Trotter error"
              value={formatValue(result.metrics.trotter_absolute_error)}
              note="Ideal circuit vs. exact evolution"
            />
            <Metric
              label="Sampling error"
              value={formatValue(result.metrics.sampling_absolute_error)}
              note="Finite-shot output vs. ideal circuit"
            />
            <Metric
              label="Total measurements"
              value={result.metrics.total_shots ?? 'Not reported'}
              note={`${result.metadata.parameters.config?.shots ?? 'Not reported'} shots per basis and time`}
            />
          </div>

          {#if result.metrics.time_series?.length}
            <MaterialsTimeSeriesChart
              points={result.metrics.time_series}
              observable={observable === 'energy' ? 'energy' : 'magnetization_z'}
              unit={selectedUnit}
            />
          {/if}

          <details class="run-details">
            <summary>Timing and model provenance</summary>
            <div class="details-grid">
              <div>
                <h3>Elapsed time</h3>
                <p>
                  Classical: {duration(result.classical?.elapsed_ms)}<br />
                  Circuit: {duration(result.quantum?.elapsed_ms)}
                </p>
              </div>
              <div>
                <h3>Model</h3>
                <p>
                  {result.metadata.hamiltonian_convention}<br />
                  Energy unit: {result.metadata.energy_unit}<br />
                  Observable unit: {result.metadata.observable_unit}
                </p>
              </div>
              <div>
                <h3>Measurement settings</h3>
                <p>
                  {result.metadata.parameters.num_spins} spins ·
                  {result.metadata.parameters.trotter_steps} Trotter steps<br />
                  {result.metadata.parameters.time_samples} time samples ·
                  {result.metadata.parameters.config?.shots ?? 'Not reported'} shots per basis<br />
                  Seed: {result.metadata.seed ?? 'unseeded'}
                </p>
              </div>
            </div>
            <p class="timing-caveat">
              Classical and circuit timings cover different workloads and are not a speedup
              comparison. Circuit time includes simulator setup, circuit construction,
              transpilation, ideal simulation, and sampling.
            </p>
          </details>
        </div>
      {:else}
        <div class="empty-state">
          <Icon name="atom" size={34} />
          <h3>No simulation has run</h3>
          <p>Adjust the small-chain parameters, then run a live comparison.</p>
        </div>
      {/if}
    </Panel>
  </div>
</ExecutionChoice>

<StudyPanel
  experiment="materials"
  request={currentRequest}
  disabled={running}
  bind:running={studying}
/>
{#if result}<button
    class="button"
    onclick={() =>
      downloadJson(
        { source: 'live_materials_api', request: currentRequest, result },
        'q-atlas-materials.json'
      )}>Download materials JSON</button
  >{/if}

<style>
  .page-heading {
    padding: 8px 0 24px;
  }
  .page-heading h1 {
    margin: 4px 0 8px;
    font-size: 30px;
    font-weight: 400;
  }
  .page-heading > div > p:last-child {
    max-width: 760px;
    margin: 0;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.65;
  }
  .provenance-note {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 20px;
    padding: 10px 14px;
    border: 1px solid var(--border);
    background: var(--surface-raised);
    color: var(--muted);
    font-size: 12px;
    line-height: 1.5;
  }
  .provenance-note :global(svg) {
    color: var(--blue);
  }
  .provenance-note strong {
    color: var(--blue);
    font-weight: 500;
  }
  .materials-grid {
    display: grid;
    grid-template-columns: minmax(270px, 0.75fr) minmax(0, 1.6fr);
    align-items: start;
    gap: 20px;
  }
  .settings-form {
    padding: 0 24px 22px;
  }
  fieldset {
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
  }
  .control-grid {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) minmax(90px, 0.9fr);
    gap: 10px 14px;
    align-items: center;
  }
  .control-grid label {
    color: var(--muted);
    font-size: 12px;
  }
  .control-grid input,
  .control-grid select {
    width: 100%;
    min-width: 0;
    min-height: 36px;
    padding: 7px 9px;
    border: 1px solid var(--border);
    border-radius: 3px;
    background: var(--surface);
    color: var(--text);
    font: 12px var(--mono);
  }
  .field-help,
  .request-issue {
    margin: 16px 0;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.65;
  }
  .request-issue {
    color: var(--accent);
  }
  .run-button {
    width: 100%;
  }
  .cancel-button {
    width: 100%;
    justify-content: center;
    margin-top: 8px;
  }
  .result-content {
    padding-bottom: 18px;
  }
  .result-provenance {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 12px;
    padding: 0 24px 16px;
    color: var(--muted);
    font-size: 11px;
  }
  .backend-badge {
    padding: 4px 7px;
    border: 1px solid var(--border);
    background: var(--surface-raised);
    color: var(--blue);
    font: 11px var(--mono);
  }
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    padding: 0 24px 18px;
  }
  .empty-state,
  .run-status,
  .error-state {
    margin: 0 24px 24px;
    padding: 22px;
    border: 1px solid var(--border);
    background: var(--surface);
  }
  .empty-state {
    text-align: center;
    color: var(--blue);
  }
  .empty-state :global(svg) {
    margin: 2px auto 10px;
  }
  .empty-state h3 {
    margin: 4px 0 8px;
    color: var(--text);
    font-size: 15px;
    font-weight: 500;
  }
  .empty-state p,
  .run-status {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
  }
  .run-status {
    margin-top: 0;
  }
  .error-state {
    border-color: var(--accent);
    background: var(--surface-raised);
    color: var(--text);
    font-size: 12px;
    line-height: 1.6;
  }
  .error-state p {
    margin: 8px 0 0;
  }
  .run-details {
    margin: 0 24px;
    border-top: 1px solid var(--border);
    color: var(--muted);
  }
  .run-details summary {
    padding: 14px 0;
    color: var(--text);
    cursor: pointer;
    font-size: 12px;
  }
  .details-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
  }
  .details-grid h3 {
    margin: 0 0 6px;
    color: var(--muted);
    font-size: 11px;
    font-weight: 500;
  }
  .details-grid p,
  .timing-caveat {
    margin: 0;
    font-size: 11px;
    line-height: 1.7;
  }
  .timing-caveat {
    padding-top: 12px;
  }
  @media (max-width: 980px) {
    .materials-grid {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 650px) {
    .metrics-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      padding-inline: 16px;
    }
    .result-provenance {
      padding-inline: 16px;
    }
    .settings-form {
      padding-inline: 18px;
    }
    .run-details {
      margin-inline: 16px;
    }
    .details-grid {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 380px) {
    .metrics-grid,
    .control-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
