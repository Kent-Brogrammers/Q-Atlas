<script lang="ts">
  import { onDestroy } from 'svelte';
  import ExecutionChoice from '#lib/components/ExecutionChoice.svelte';
  import StudyPanel from '#lib/components/StudyPanel.svelte';
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
  import { measureTrials, summarizeTrials, trialCurve } from '#lib/search/trials.ts';
  import { buildSearchExport, loadRecordedDemo } from '#lib/search/recorded.ts';
  import type { RecordingProvenance } from '#lib/search/recorded.ts';
  import { intervalLabel, samplingInterval } from '#lib/search/uncertainty.ts';
  import { gateResources } from '#lib/search/resources.ts';

  type RunMode = 'single' | 'curve' | 'trials';

  let settings = $state(defaultSettings());
  let maxIteration = $state<number | undefined>(6);
  let repetitions = $state<number | undefined>(3);
  let completedMode = $state<RunMode>('single');
  let recording = $state<RecordingProvenance | null>(null);
  let results = $state<SearchResult[]>([]);
  let selectedIndex = $state(0);
  let loading = $state(false);
  let studying = $state(false);
  let studyRequest = $derived.by(() => {
    try {
      return buildRequest(settings);
    } catch {
      return null;
    }
  });
  let error = $state('');
  let progress = $state('');
  let controller: AbortController | undefined;
  let selected = $derived(results[selectedIndex]);
  let resources = $derived(selected ? gateResources(selected) : null);
  let summary = $derived(
    completedMode === 'trials' && results.length ? summarizeTrials(results) : null
  );
  let points = $derived(summary ? trialCurve(summary) : curvePoints(results));
  onDestroy(() => controller?.abort());

  function clearResults() {
    results = [];
    selectedIndex = 0;
    error = '';
    progress = '';
    completedMode = 'single';
    recording = null;
  }

  function loadRecording(mode: 'curve' | 'trials') {
    if (loading || studying) return;
    clearResults();
    try {
      const saved = loadRecordedDemo(mode);
      results = saved.results;
      completedMode = mode;
      recording = saved.provenance;
      selectedIndex = mode === 'curve' ? 2 : 0;
      const parameters = saved.results[selectedIndex].metadata.parameters;
      settings = {
        numQubits: parameters.num_qubits,
        targets: parameters.marked_states.join(', '),
        automatic: false,
        iterations: parameters.iterations ?? undefined,
        shots: parameters.config?.shots,
        seed: parameters.config?.seed,
        timeout: parameters.config?.timeout_seconds
      };
      if (mode === 'curve') maxIteration = saved.results.length - 1;
      if (mode === 'trials') repetitions = saved.results.length;
      progress = 'Previously measured demo loaded. No live request was made.';
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'The recorded demo could not load.';
    }
  }

  async function run(mode: RunMode) {
    if (loading || studying) return;
    clearResults();
    loading = true;
    controller = new AbortController();
    const signal = controller.signal;
    try {
      const measured =
        mode === 'curve'
          ? await measureSweep(settings, maxIteration, api.search, signal, (done, total) => {
              progress = `Measured ${done} of ${total} iteration points.`;
            })
          : mode === 'trials'
            ? await measureTrials(settings, repetitions, api.search, signal, (done, total) => {
                progress = `Completed ${done} of ${total} seeded trials.`;
              })
            : [await api.search(buildRequest(settings), signal)];
      signal.throwIfAborted();
      curvePoints(measured);
      results = measured;
      completedMode = mode;
      selectedIndex = mode === 'curve' ? Math.min(2, results.length - 1) : 0;
      progress =
        mode === 'curve'
          ? `Curve complete: ${results.length} measured points.`
          : mode === 'trials'
            ? `Repeated trials complete: ${results.length} recorded runs.`
            : 'Comparison complete.';
    } catch (cause) {
      results = [];
      progress = '';
      error = signal.aborted
        ? 'Stopped. No incomplete results are displayed.'
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
    const blob = new Blob(
      [JSON.stringify(buildSearchExport(completedMode, results, recording), null, 2)],
      {
        type: 'application/json'
      }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = recording ? 'q-atlas-search-recorded-demo.json' : 'q-atlas-search-results.json';
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
    <h1>Grover Search</h1>
    <p>Compare Grover amplification with classical search, one small instance at a time.</p>
  </div>
  <span class="badge">{recording ? 'Previously measured demo' : 'Local Aer simulator'}</span>
</header>
<p class="notice">
  Targets are supplied to construct the oracle. This demonstrates search under an oracle model;
  simulator runtime is not evidence of quantum speedup.
</p>
{#if error}<div class="error" role="alert">
    <strong>Search could not complete.</strong>
    {error}
    <p>
      For connection errors, start the backend and check its configured address. Recorded results
      load only when you select a demo button.
    </p>
  </div>{/if}

<ExecutionChoice experiment="search" request={studyRequest}>
  <div class="search-layout">
    <aside aria-label="Search configuration">
      <Panel title="Configure search" subtitle="Bitstrings put qubit 0 on the left">
        <form
          novalidate
          onsubmit={(event) => {
            event.preventDefault();
            void run('single');
          }}
          oninput={clearResults}
        >
          <fieldset disabled={loading || studying}>
            <details>
              <summary>Change search settings</summary>
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
                Separate unique targets with commas or spaces. Preserve leading zeros, for example
                001, 110.
              </p>
              <label class="check"
                ><input type="checkbox" bind:checked={settings.automatic} /> Suggest iterations for a
                single run</label
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
            </details>
            <button class="button primary" type="submit">Run comparison</button>
            <details>
              <summary>Advanced: curves &amp; repeated trials</summary>
              <div class="curve-controls">
                <label for="last-iteration">Curve: iterations 0 through</label><input
                  id="last-iteration"
                  type="number"
                  min="0"
                  max="12"
                  step="1"
                  required
                  bind:value={maxIteration}
                /><button class="button" type="button" onclick={() => void run('curve')}
                  >Measure probability curve</button
                >
              </div>
              <p class="hint">
                A curve runs up to 13 independent requests in sequence, using the same shots and
                seed. More iterations can reduce success.
              </p>
              <div class="curve-controls">
                <label for="repetitions">Repeated trials (same iteration setting)</label>
                <input
                  id="repetitions"
                  type="number"
                  min="2"
                  max="5"
                  step="1"
                  bind:value={repetitions}
                />
                <button class="button" type="button" onclick={() => void run('trials')}
                  >Run repeated trials</button
                >
                <p class="hint">
                  Two to five runs at the single-run iteration setting. Seeds increment from your
                  chosen seed; every raw run is retained.
                </p>
              </div>
            </details>
          </fieldset>
        </form>
        {#if loading}<div class="running">
            <button class="button small" onclick={() => controller?.abort()}>Stop requests</button>
            <p class="hint">
              The current backend worker may finish or reach its timeout after you stop.
            </p>
          </div>{/if}
        <div class="recorded-controls">
          <strong>Previously measured demo</strong>
          <p class="hint">
            Explicit offline fallback with recorded settings and timings. These buttons make no live
            requests.
          </p>
          <button class="button small" disabled={loading} onclick={() => loadRecording('curve')}
            >Load recorded curve</button
          >
          <button class="button small" disabled={loading} onclick={() => loadRecording('trials')}
            >Load recorded trials</button
          >
        </div>
      </Panel>
    </aside>

    <div class="results" aria-busy={loading}>
      {#if recording}<div class="recorded-banner" role="status">
          <strong>Previously measured demo — not a live run</strong>
          <p>
            Recorded {recording.recorded_at_utc}. Source revision {recording.source_revision.slice(
              0,
              7
            )}{recording.working_tree_dirty ? ' (working tree had pending changes)' : ''}. Timings
            belong to the recorded simulator environment. Changing inputs clears this recording.
          </p>
        </div>{/if}
      <p class="progress" role="status" aria-live="polite">
        {loading ? progress || 'Running the local search benchmark…' : progress}
      </p>
      <Panel
        title="Success probability"
        subtitle="Measured outcomes and ideal theory at each iteration"
      >
        <SearchProbabilityChart
          {points}
          measurementLabel={summary ? 'Mean success across trials' : 'Measured Aer shots'}
        />
      </Panel>
      {#if summary}
        <Panel
          title="Repeated-run summary"
          subtitle={`${summary.trialCount} seeded trials at iteration ${summary.iteration}`}
        >
          <div class="metrics trial-metrics">
            <div>
              <span>Mean success</span><strong>{percentage(summary.meanSuccessProbability)}</strong>
            </div>
            <div>
              <span>Observed min / max</span><strong
                >{percentage(summary.minimumSuccessProbability)} / {percentage(
                  summary.maximumSuccessProbability
                )}</strong
              >
            </div>
            <div>
              <span>Sample standard deviation</span><strong
                >{(summary.sampleStandardDeviation * 100).toFixed(2)} pp</strong
              >
            </div>
            <div><span>Total shots</span><strong>{summary.totalShots}</strong></div>
          </div>
          <div class="table-scroll">
            <table>
              <caption
                >Median solver time across all recorded trials. No warm-up run is excluded.</caption
              >
              <thead
                ><tr><th scope="col">Classical search</th><th scope="col">Grover shot batch</th></tr
                ></thead
              >
              <tbody
                ><tr
                  ><td>{milliseconds(summary.medianClassicalMs)}</td><td
                    >{milliseconds(summary.medianQuantumMs)}</td
                  ></tr
                ></tbody
              >
            </table>
          </div>
          <p class="explanation">
            Seeds: {summary.seeds.join(', ')}. {summary.shotsPerTrial} shots per trial. The range and
            sample standard deviation describe variation across these runs; pp means percentage points.
            Neither is a confidence interval. Repeated simulator runs do not establish quantum speedup.
          </p>
        </Panel>
      {/if}
      {#if selected}
        <Panel
          title={`${summary ? `Trial ${selectedIndex + 1} · ` : ''}Iteration ${selected.metadata.parameters.iterations}`}
          subtitle={recording
            ? 'Previously measured backend results · not a live run'
            : 'Real backend results · one simulator run per point'}
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
                  ><th scope="col">Comparison</th><th scope="col">Classical search</th><th
                    scope="col">Grover simulation</th
                  ></tr
                ></thead
              >
              <tbody>
                <tr
                  ><th scope="row">Gates per transpiled circuit</th><td>Not applicable</td>
                  <td>{resources?.total ?? 'Not available'}</td></tr
                >
                <tr
                  ><th scope="row">Gate breakdown</th><td>Not applicable</td>
                  <td>{resources?.breakdown ?? 'Not available'}</td></tr
                >
                <tr
                  ><th scope="row">95% sampling interval (Wilson)</th><td>Not applicable</td>
                  <td>{intervalLabel(samplingInterval(selected))}</td></tr
                >
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
            unmarked. Total quantum oracle calls are iteration count times shots, not primitive
            gates or measured simulator operations. Gate counts describe one Aer-transpiled circuit,
            excluding measurements, reset and barriers; retained composite gates count once. They
            are not a native hardware gate count or a shot-batch total. These timings are not
            matched-success speedup measurements.
          </p>
        </Panel>
        <Panel
          title={summary ? 'Individual trial measurements' : 'Iteration measurements'}
          subtitle={summary
            ? 'Select a trial to inspect its raw comparison'
            : 'Select an iteration to inspect its comparison'}
        >
          <div class="table-scroll">
            <table>
              <caption
                >{results.length} measured {summary
                  ? 'trials'
                  : `point${results.length === 1 ? '' : 's'}`}; no illustrative results.</caption
              >
              <thead
                ><tr
                  ><th scope="col">{summary ? 'Trial / iteration' : 'Iteration'}</th><th scope="col"
                    >Seed</th
                  ><th scope="col">Measured</th><th scope="col">95% sampling interval</th><th
                    scope="col">Theory</th
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
                        >{summary ? `Trial ${index + 1} / ` : 'Iteration '}{result.metadata
                          .parameters.iterations}</button
                      ></th
                    ><td>{result.metadata.seed ?? 'Not available'}</td><td
                      >{percentage(result.metrics.success_probability)}</td
                    ><td>{intervalLabel(samplingInterval(result))}</td><td
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
            Targets: <span class="mono"
              >{selected.metadata.parameters.marked_states.join(', ')}</span
            >. Seed: {selected.metadata.seed ?? 'Not set'}. Shots: {selected.metrics.shots ??
              'Not available'}. Repetitions per point: {selected.metadata.repetitions ?? 1}.
          </p>
          <p>
            Package versions: {Object.entries(selected.metadata.versions ?? {})
              .map(([name, value]) => `${name} ${value}`)
              .join(' · ')}
          </p>
          <p>
            {summary
              ? 'Repeated trials use distinct recorded seeds at the same iteration setting.'
              : 'Curves use the same seed at every iteration.'} Each raw run has a pointwise 95% Wilson
            interval computed from successful and total shots, assuming independent shots at a fixed success
            probability. The nominal 95% refers to repeated-sampling coverage, not a probability assigned
            to this particular interval. These approximate intervals cover sampling uncertainty, not hardware
            noise, model error or a whole curve simultaneously. The repeated-trial chart retains its observed
            min/max range; it does not pool shots or display an interval for the mean. Missing shot counts
            show “Not available.” Editing inputs clears previous results. Downloaded JSON contains the
            raw counts needed to reproduce intervals, every completed point and its settings.
          </p>
        </details>
      {/if}
    </div>
  </div>
</ExecutionChoice>
<StudyPanel experiment="search" request={studyRequest} disabled={loading} bind:running={studying} />

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
    background: var(--surface);
    border-radius: 4px;
    font-size: 12px;
  }
  .notice {
    padding: 14px 18px;
    border-left: 3px solid var(--blue);
    background: color-mix(in srgb, var(--blue) 6%, var(--surface));
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
    border: 1px solid var(--border);
    border-radius: 3px;
    background: var(--surface);
    color: var(--text);
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
  input[type='checkbox'] {
    accent-color: var(--blue);
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
  .recorded-controls {
    padding: 18px 24px;
    border-top: 1px solid var(--border);
    font-size: 13px;
  }
  .recorded-controls .button {
    margin: 4px 4px 4px 0;
  }
  .recorded-banner {
    border: 1px solid var(--accent, var(--violet));
    background: color-mix(in srgb, var(--accent, var(--violet)) 8%, var(--surface));
    color: var(--text);
    padding: 16px 20px;
    border-radius: 4px;
    font-size: 13px;
  }
  .recorded-banner p {
    line-height: 1.6;
    margin-bottom: 0;
    overflow-wrap: anywhere;
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
  .trial-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .trial-metrics strong {
    font-size: clamp(14px, 1.6vw, 20px);
    overflow-wrap: anywhere;
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
    background: color-mix(in srgb, var(--blue) 10%, var(--surface));
  }
  .point-button {
    border: 0;
    background: transparent;
    color: var(--blue);
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
    background: var(--surface);
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
    border: 1px solid var(--error, var(--accent, var(--violet)));
    padding: 16px;
    margin-bottom: 20px;
    color: var(--text);
    background: color-mix(in srgb, var(--error, var(--accent, var(--violet))) 6%, var(--surface));
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
