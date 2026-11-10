<script lang="ts">
  import { onDestroy } from 'svelte';
  import Panel from '#lib/components/Panel.svelte';
  import SearchProbabilityChart from '#lib/search/SearchProbabilityChart.svelte';
  import {
    buildRequest,
    curvePoints,
    defaultSettings,
    measureSweep,
    milliseconds,
    percentage
  } from '#lib/search/live.ts';
  import { api, ApiError } from '../../api/client.ts';
  import type { SearchResult } from '../../types/index.ts';

  let settings = $state(defaultSettings());
  let maxIteration = $state<number | undefined>(6);
  let results = $state<SearchResult[]>([]);
  let selectedIndex = $state(0);
  let loading = $state(false);
  let error = $state('');
  let progress = $state('');
  let controller: AbortController | undefined;
  let selected = $derived(results[selectedIndex]);
  let points = $derived(curvePoints(results));
  onDestroy(() => controller?.abort());

  function clearResults() {
    results = [];
    selectedIndex = 0;
    error = '';
    progress = '';
  }

  async function run(sweep: boolean) {
    if (loading) return;
    clearResults();
    loading = true;
    controller = new AbortController();
    const signal = controller.signal;
    try {
      const measured = sweep
        ? await measureSweep(settings, maxIteration, api.search, signal, (done, total) => {
            progress = `Measured ${done} of ${total} iteration points.`;
          })
        : [await api.search(buildRequest(settings), signal)];
      signal.throwIfAborted();
      curvePoints(measured);
      results = measured;
      selectedIndex = sweep ? Math.min(2, results.length - 1) : 0;
      progress = sweep
        ? `Curve complete: ${results.length} measured points.`
        : 'Comparison complete.';
    } catch (cause) {
      results = [];
      progress = '';
      error = signal.aborted
        ? 'Stopped. No incomplete curve is displayed.'
        : cause instanceof ApiError
          ? [
              cause.message,
              ...(cause.body.error.diagnostics ?? []).map((item) => item.message)
            ].join(' ')
          : cause instanceof Error
            ? cause.message
            : 'The search experiment failed.';
    } finally {
      loading = false;
    }
  }

  function download() {
    const blob = new Blob([JSON.stringify({ source: 'live_search_api', results }, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'q-atlas-search-results.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>

<svelte:head>
  <title>Grover Search · Q-Atlas</title>
  <meta
    name="description"
    content="Measure Grover success probabilities and compare oracle queries with classical search on a local simulator."
  />
</svelte:head>

<header class="heading">
  <div>
    <p class="eyebrow">Search benchmark</p>
    <h1>Find the target. Explore the probability.</h1>
    <p>Compare Grover amplification with classical search, one small instance at a time.</p>
  </div>
  <span class="badge">Local Aer simulator</span>
</header>
<p class="notice">
  Targets are supplied to construct the oracle. This demonstrates search under an oracle model;
  simulator runtime is not evidence of quantum speedup.
</p>
{#if error}<div class="error" role="alert">
    <strong>Search could not complete.</strong>
    {error}
    <p>
      For connection errors, start the backend at http://127.0.0.1:8000. Errors never load example
      results.
    </p>
  </div>{/if}

<div class="search-layout">
  <aside aria-label="Search configuration">
    <Panel title="Configure search" subtitle="Bitstrings put qubit 0 on the left">
      <form
        novalidate
        onsubmit={(event) => {
          event.preventDefault();
          void run(false);
        }}
        oninput={clearResults}
      >
        <fieldset disabled={loading}>
          <label for="qubits">Qubits</label><input
            id="qubits"
            type="number"
            min="1"
            max="6"
            step="1"
            required
            bind:value={settings.numQubits}
          />
          <label for="targets">Marked bitstrings</label><textarea
            id="targets"
            rows="2"
            required
            spellcheck="false"
            bind:value={settings.targets}
            aria-describedby="targets-help"
          ></textarea>
          <p id="targets-help" class="hint">
            Separate unique targets with commas or spaces. Preserve leading zeros, for example 001,
            110.
          </p>
          <label class="check"
            ><input type="checkbox" bind:checked={settings.automatic} /> Suggest iterations for a single
            run</label
          >
          <label for="iterations">Single-run iterations</label><input
            id="iterations"
            type="number"
            min="0"
            max="32"
            step="1"
            disabled={settings.automatic}
            required={!settings.automatic}
            bind:value={settings.iterations}
          />
          <label for="shots">Shots per iteration point</label><input
            id="shots"
            type="number"
            min="1"
            max="10000"
            step="1"
            required
            bind:value={settings.shots}
          />
          <label for="seed">Seed</label><input
            id="seed"
            type="number"
            min="0"
            max={2 ** 32 - 1}
            step="1"
            required
            bind:value={settings.seed}
          />
          <label for="timeout">Timeout per point (seconds)</label><input
            id="timeout"
            type="number"
            min="0.001"
            max="60"
            step="any"
            required
            bind:value={settings.timeout}
          />
          <button class="button primary" type="submit">Run comparison</button>
          <div class="curve-controls">
            <label for="last-iteration">Curve: iterations 0 through</label><input
              id="last-iteration"
              type="number"
              min="0"
              max="12"
              step="1"
              required
              bind:value={maxIteration}
            /><button class="button" type="button" onclick={() => void run(true)}
              >Measure probability curve</button
            >
          </div>
          <p class="hint">
            A curve runs up to 13 independent requests in sequence, using the same shots and seed.
            More iterations can reduce success.
          </p>
        </fieldset>
      </form>
      {#if loading}<div class="running">
          <button class="button small" onclick={() => controller?.abort()}>Stop requests</button>
          <p class="hint">
            The current backend worker may finish or reach its timeout after you stop.
          </p>
        </div>{/if}
    </Panel>
  </aside>

  <div class="results" aria-busy={loading}>
    <p class="progress" role="status" aria-live="polite">
      {loading ? progress || 'Running the local search benchmark…' : progress}
    </p>
    <Panel
      title="Success probability"
      subtitle="Measured outcomes and ideal theory at each iteration"
    >
      <SearchProbabilityChart {points} />
    </Panel>
    {#if selected}
      <Panel
        title={`Iteration ${selected.metadata.parameters.iterations}`}
        subtitle="Real backend results · one simulator run per point"
      >
        <div class="metrics">
          <div>
            <span>Measured success</span><strong
              >{percentage(selected.metrics.success_probability)}</strong
            >
          </div>
          <div>
            <span>Ideal success</span><strong
              >{percentage(selected.metrics.theoretical_success_probability)}</strong
            >
          </div>
          <div>
            <span>Oracle calls / shot</span><strong
              >{selected.metrics.quantum_oracle_queries ?? 'Not available'}</strong
            >
          </div>
          <div>
            <span>Transpiled depth</span><strong
              >{selected.metrics.circuit_depth ?? 'Not available'}</strong
            >
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <caption>Query counts and measured runtime describe different costs.</caption>
            <thead
              ><tr
                ><th scope="col">Comparison</th><th scope="col">Classical search</th><th scope="col"
                  >Grover simulation</th
                ></tr
              ></thead
            >
            <tbody>
              <tr
                ><th scope="row">Returned bitstring</th><td class="mono"
                  >{selected.classical?.best_bitstring ?? 'Not available'}</td
                ><td class="mono"
                  >{selected.quantum?.best_bitstring ?? 'Not available'} (most frequent)</td
                ></tr
              >
              <tr
                ><th scope="row">Expected / worst queries</th><td
                  >{selected.metrics.classical_expected_queries ?? 'Not available'} / {selected
                    .metrics.classical_worst_case_queries ?? 'Not available'}</td
                ><td
                  >{selected.metrics.quantum_oracle_queries ?? 'Not available'} per shot, with success
                  shown above</td
                ></tr
              >
              <tr
                ><th scope="row">Observed classical checks</th><td
                  >{selected.metrics.classical_observed_queries ?? 'Not available'}</td
                ><td>Not applicable</td></tr
              >
              <tr
                ><th scope="row">Successful shots / total shots</th><td>Not applicable</td><td
                  >{selected.metrics.successful_shots ?? 'Not available'} / {selected.metrics
                    .shots ?? 'Not available'}</td
                ></tr
              >
              <tr
                ><th scope="row">Oracle calls across shot batch</th><td>Not applicable</td><td
                  >{selected.metrics.quantum_total_oracle_queries ?? 'Not available'}</td
                ></tr
              >
              <tr
                ><th scope="row">Solver wall time</th><td
                  >{milliseconds(selected.classical?.elapsed_ms)}</td
                ><td>{milliseconds(selected.quantum?.elapsed_ms)}</td></tr
              >
              <tr
                ><th scope="row">Transpilation</th><td>Not applicable</td><td
                  >{milliseconds(selected.quantum?.timing.transpilation_ms)}</td
                ></tr
              >
              <tr
                ><th scope="row">Sampling</th><td>Not applicable</td><td
                  >{milliseconds(selected.quantum?.timing.sampling_ms)}</td
                ></tr
              >
            </tbody>
          </table>
        </div>
        <p class="explanation">
          The classical run stops at its first match. Quantum wall time includes the whole shot
          batch; the query count is per circuit execution. The most frequent quantum output may be
          unmarked. Total quantum oracle calls are iteration count times shots, not primitive gates
          or measured simulator operations. These timings are not matched-success speedup
          measurements.
        </p>
      </Panel>
      <Panel
        title="Iteration measurements"
        subtitle="Select an iteration to inspect its comparison"
      >
        <div class="table-scroll">
          <table>
            <caption
              >{results.length} measured point{results.length === 1 ? '' : 's'}; no illustrative
              results.</caption
            >
            <thead
              ><tr
                ><th scope="col">Iteration</th><th scope="col">Measured</th><th scope="col"
                  >Theory</th
                ><th scope="col">Shots</th><th scope="col">Depth</th></tr
              ></thead
            >
            <tbody
              >{#each results as result, index}<tr class:selected={selectedIndex === index}
                  ><th scope="row"
                    ><button
                      class="point-button"
                      aria-pressed={selectedIndex === index}
                      onclick={() => (selectedIndex = index)}
                      >Iteration {result.metadata.parameters.iterations}</button
                    ></th
                  ><td>{percentage(result.metrics.success_probability)}</td><td
                    >{percentage(result.metrics.theoretical_success_probability)}</td
                  ><td>{result.metrics.shots ?? 'Not available'}</td><td
                    >{result.metrics.circuit_depth ?? 'Not available'}</td
                  ></tr
                >{/each}</tbody
            >
          </table>
        </div>
        <div class="export">
          <button class="button small" onclick={download}>Download measured JSON</button>
        </div>
      </Panel>
      <details class="method">
        <summary>Method, timing scope, and reproducibility</summary>
        <p>{selected.metadata.oracle_assumptions}</p>
        <p>
          Targets: <span class="mono">{selected.metadata.parameters.marked_states.join(', ')}</span
          >. Seed: {selected.metadata.seed ?? 'Not set'}. Shots: {selected.metrics.shots ??
            'Not available'}. Repetitions per point: {selected.metadata.repetitions ?? 1}.
        </p>
        <p>
          Package versions: {Object.entries(selected.metadata.versions ?? {})
            .map(([name, value]) => `${name} ${value}`)
            .join(' · ')}
        </p>
        <p>
          Curves use the same seed at every iteration. Shot noise remains; no confidence interval or
          repeated-run distribution is claimed. Editing inputs clears previous results. Downloaded
          JSON contains every completed point and its settings.
        </p>
      </details>
    {/if}
  </div>
</div>

<style>
  .heading {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: flex-start;
    margin: 10px 0 22px;
  }
  h1 {
    margin: 7px 0 12px;
    font-size: clamp(24px, 3vw, 34px);
    font-weight: 400;
    line-height: 1.25;
  }
  .heading p,
  .notice {
    color: var(--muted);
    line-height: 1.65;
    font-size: 14px;
  }
  .heading p {
    margin: 0;
  }
  .badge {
    flex-shrink: 0;
    padding: 7px 10px;
    border: 1px solid var(--border);
    background: white;
    border-radius: 4px;
    font-size: 12px;
  }
  .notice {
    padding: 14px 18px;
    border-left: 3px solid var(--blue);
    background: #edf4ff;
    margin: 0 0 24px;
  }
  .search-layout {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 24px;
    align-items: start;
  }
  .results {
    display: grid;
    gap: 20px;
    min-width: 0;
  }
  .progress {
    margin: 0;
    font-size: 13px;
    color: var(--muted);
  }
  .progress:empty {
    display: none;
  }
  form {
    padding: 0 24px 18px;
  }
  fieldset {
    padding: 0;
    margin: 0;
    border: 0;
    min-width: 0;
  }
  label {
    display: block;
    font-size: 13px;
    margin: 14px 0 7px;
  }
  input:not([type='checkbox']),
  textarea {
    display: block;
    width: 100%;
    min-height: 40px;
    border: 1px solid #cdd7e3;
    border-radius: 3px;
    background: white;
    padding: 8px 10px;
    font-family: var(--mono);
    font-size: 13px;
  }
  textarea {
    resize: vertical;
  }
  .check {
    display: flex;
    align-items: center;
    gap: 9px;
    line-height: 1.5;
  }
  .hint {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
  }
  fieldset > .button {
    width: 100%;
    justify-content: center;
    margin-top: 18px;
  }
  .curve-controls {
    margin-top: 22px;
    border-top: 1px solid var(--border);
    padding-top: 4px;
  }
  .curve-controls .button {
    width: 100%;
    margin-top: 12px;
    justify-content: center;
    font-size: 13px;
  }
  .running {
    padding: 0 24px 18px;
  }
  .metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    padding: 0 24px 22px;
  }
  .metrics span {
    display: block;
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 7px;
  }
  .metrics strong {
    font: 23px var(--mono);
  }
  .table-scroll {
    overflow-x: auto;
    padding: 0 24px 18px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    text-align: left;
  }
  caption {
    text-align: left;
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 12px;
    line-height: 1.6;
  }
  th,
  td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }
  th {
    font-weight: 500;
  }
  tr.selected {
    background: #edf4ff;
  }
  .point-button {
    border: 0;
    background: transparent;
    color: #0f62fe;
    padding: 0;
    text-decoration: underline;
    white-space: nowrap;
  }
  .explanation {
    color: var(--muted);
    padding: 0 24px 18px;
    font-size: 12px;
    line-height: 1.7;
    margin: 0;
  }
  .export {
    padding: 0 24px 20px;
  }
  .method {
    border: 1px solid var(--border);
    background: white;
    padding: 18px 24px;
    border-radius: 5px;
    font-size: 13px;
  }
  summary {
    cursor: pointer;
    font-weight: 500;
  }
  .method p {
    color: var(--muted);
    line-height: 1.7;
    overflow-wrap: anywhere;
  }
  .error {
    border: 1px solid #edbbbb;
    padding: 16px;
    margin-bottom: 20px;
    color: #922c2c;
    background: #fff8f8;
    font-size: 13px;
    line-height: 1.6;
  }
  .error p {
    margin-bottom: 0;
  }
  @media (max-width: 1100px) {
    .search-layout {
      grid-template-columns: 260px minmax(0, 1fr);
      gap: 16px;
    }
    .metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (max-width: 760px) {
    .search-layout {
      grid-template-columns: minmax(0, 1fr);
    }
    .heading {
      flex-direction: column;
    }
  }
</style>
