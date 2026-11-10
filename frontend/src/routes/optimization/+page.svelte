<script lang="ts">
  import { fade } from 'svelte/transition';
  import { prefersReducedMotion } from 'svelte/motion';
  import type { OptimizationRequest } from '#lib/types/contracts.ts';
  import { graphs, getExampleRun } from '#lib/data/fixtures.ts';
  import Panel from '#lib/components/Panel.svelte';
  import Icon from '#lib/components/Icon.svelte';
  import Metric from '#lib/components/Metric.svelte';
  import GraphView from '#lib/components/GraphView.svelte';
  import LineChart from '#lib/components/LineChart.svelte';
  import Histogram from '#lib/components/Histogram.svelte';
  import ExampleNotice from '#lib/components/ExampleNotice.svelte';
  import FeatureBanner from '#lib/components/FeatureBanner.svelte';
  import SolverComparison from '#lib/components/SolverComparison.svelte';

  let selectedId = $state('prism');
  let loadedId = $state('prism');
  let layers = $state(2);
  let shots = $state(1024);
  let seed = $state<number | undefined>(42);
  const optimizer = 'COBYLA' as const;
  let run = $state(getExampleRun('prism'));
  let graph = $derived(graphs.find((item) => item.id === loadedId)!);
  let graphTab = $state<'graph' | 'qubo'>('graph');
  let chartTab = $state<'expected' | 'sampled'>('expected');
  let showExample = $state(false);
  let status = $state('Graph preset ready. No solver has run.');
  let revision = $state(0);
  let copyLabel = $state('Copy QUBO');
  let gap = $derived(
    (run.comparison.quantum?.objective ?? 0) - (run.comparison.classical?.objective ?? 0)
  );

  function loadExample(event?: SubmitEvent) {
    event?.preventDefault();
    run = getExampleRun(selectedId);
    loadedId = selectedId;
    showExample = true;
    revision += 1;
    status = `${graph.name}: example data displayed. No solver ran; controls do not change example values.`;
  }

  function reset() {
    selectedId = 'prism';
    layers = 2;
    shots = 1024;
    seed = 42;
    graphTab = 'graph';
    chartTab = 'expected';
    selectGraph();
  }

  function selectGraph(id = selectedId) {
    selectedId = id;
    loadedId = selectedId;
    run = getExampleRun(selectedId);
    showExample = false;
    revision += 1;
    copyLabel = 'Copy QUBO';
    status = `${graph.name}: graph preset ready. No solver has run.`;
  }

  async function copyQubo() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(graph.qubo, null, 2));
      copyLabel = 'Copied';
    } catch {
      copyLabel = 'Copy unavailable';
    }
  }

  function exportExample() {
    const data = {
      kind: 'ui_example',
      example_comparison: run.comparison,
      example_chart_data: {
        expected: run.expected,
        best_sampled: run.bestSampled,
        histogram: run.histogram
      },
      request_preview: {
        problem: { kind: 'qubo', qubo: graph.qubo },
        config: { p: layers, shots, seed: seed ?? 42, optimizer }
      } satisfies OptimizationRequest,
      notice:
        'Illustrative UI example. No experiment was executed. Controls do not change example values.'
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = `q-atlas-ui-example-${loadedId}.json`;
    link.click();
    URL.revokeObjectURL(url);
    status = 'Exported labeled example JSON. No measured results were included.';
  }
</script>

<svelte:head><title>Max-Cut Optimization · Q-Atlas</title></svelte:head>

<header class="page-heading">
  <div>
    <h1>Max-Cut Optimization</h1>
    <p>Graph configuration and classical versus QAOA result comparison.</p>
  </div>
  <div class="page-actions">
    <button class="button quiet small" onclick={reset}><Icon name="reset" size={14} />Reset</button
    ><button class="button small" onclick={exportExample} disabled={!showExample}
      >Export example<Icon name="download" size={14} /></button
    >
  </div>
</header>
<ExampleNotice />

<div class="optimization-intro">
  <div class="lab-introduction">
    <FeatureBanner
      title="Classical vs quantum optimization"
      description="Max-Cut assigns vertices to two sets to maximize crossing edges. Its QUBO minimizes the negative cut size. QAOA and classical solver execution are not connected."
    >
      <a href="#experiment-settings">Simulation settings<Icon name="arrow" size={15} /></a>
      <a href="#benchmark-results">Benchmark results<Icon name="arrow" size={15} /></a>
    </FeatureBanner>
    <div class="lab-description">
      <h2>QAOA workflow</h2>
      <p>
        QAOA alternates cost and mixing layers while a classical optimizer adjusts circuit angles.
        Compare sampled solutions against the same QUBO's classical baseline. Load example data
        below to inspect the result displays without executing a solver.
      </p>
    </div>
  </div>
  <Panel
    title="Solver comparison"
    subtitle={showExample
      ? 'Example data · not measured results'
      : 'No benchmark results available'}
  >
    <SolverComparison result={showExample ? run.comparison : null} optimum={graph.optimumCut} />
  </Panel>
</div>

<div class="experiment-context">
  <div>
    <span class="context-rule"></span>
    <h2>{graph.name}</h2>
    <span class="context-separator">/</span><span class="context-detail">Unweighted Max-Cut</span>
  </div>
  <span class="context-detail mono">QUBO · minimize</span>
</div>

<div class="metrics-grid">
  <Metric
    label="Problem size"
    value={graph.nodes.length}
    unit="variables"
    note={`${graph.edges.length} edges · binary variables`}
  /><Metric
    label="Reference cut"
    value={graph.optimumCut}
    unit={`/ ${graph.edges.length}`}
    note="Known optimum for this graph"
    tone="cyan"
  /><Metric
    label="Best-sample gap"
    value={showExample ? gap.toFixed(2) : 'Not run'}
    note={showExample
      ? 'Example QAOA objective − reference objective'
      : 'No QAOA samples available'}
    tone="violet"
  /><Metric label="Circuit depth" value="Not measured" note="Circuit generation is not connected" />
</div>

<div class="lab-grid" id="experiment-settings">
  <Panel title="Simulation settings" className="controls-panel">
    <form class="controls-form" onsubmit={loadExample}>
      <label for="graph-preset">Graph preset</label><select
        id="graph-preset"
        bind:value={selectedId}
        onchange={(event) => selectGraph(event.currentTarget.value)}
        >{#each graphs as item}<option value={item.id}
            >{item.name} · {item.nodes.length} nodes</option
          >{/each}</select
      >
      <div class="control-divider"></div>
      <div class="range-heading">
        <label for="layers">QAOA layers</label><output for="layers">p = {layers}</output>
      </div>
      <input id="layers" type="range" min="1" max="5" step="1" bind:value={layers} />
      <div class="range-labels"><span>1</span><span>5</span></div>
      <fieldset>
        <legend>Measurement shots</legend>
        <div class="shot-options">
          {#each [512, 1024, 2048] as count}<label class:selected={shots === count}
              ><input
                type="radio"
                name="shots"
                value={count}
                bind:group={shots}
              />{count.toLocaleString()}</label
            >{/each}
        </div>
      </fieldset>
      <label for="optimizer">Classical optimizer</label><select id="optimizer" value={optimizer}
        ><option>COBYLA</option><option disabled>SPSA (not supported by the API)</option></select
      >
      <label for="seed">Random seed</label><input
        id="seed"
        type="number"
        min="0"
        max="4294967295"
        step="1"
        required
        bind:value={seed}
      />
      <div class="backend-preview">
        <Icon name="terminal" size={16} />
        <div><strong>Planned simulator</strong><span>Qiskit Aer · integration pending</span></div>
      </div>
      <button type="submit" class="button primary load-button"
        >Load example data<Icon name="arrow" size={16} /></button
      >
      <p class="control-note">
        Settings preview a future backend request. Loading example data does not use these settings
        or run a solver.
      </p>
    </form>
  </Panel>

  <Panel title="Graph and QUBO" className="problem-panel">
    {#snippet toolbar()}<div class="segmented">
        <button
          class:selected={graphTab === 'graph'}
          aria-pressed={graphTab === 'graph'}
          onclick={() => (graphTab = 'graph')}>Graph</button
        ><button
          class:selected={graphTab === 'qubo'}
          aria-pressed={graphTab === 'qubo'}
          onclick={() => {
            graphTab = 'qubo';
            copyLabel = 'Copy QUBO';
          }}>QUBO</button
        >
      </div>{/snippet}
    {#if graphTab === 'graph'}{#key revision}<GraphView {graph} />{/key}{:else}<div
        class="qubo-view"
      >
        <div class="qubo-toolbar">
          <span class="eyebrow">Canonical QUBO · JSON</span><button
            class="button small quiet"
            onclick={copyQubo}>{copyLabel}<Icon name="copy" size={13} /></button
          >
        </div>
        <pre class="code-block">{JSON.stringify(graph.qubo, null, 2)}</pre>
        <p>
          Assignment index i means x[i]. API bitstrings list x[0] first; Qiskit count strings must
          be converted at the sampler boundary.
        </p>
      </div>{/if}
    <div class="objective-strip">
      <span class="eyebrow">Objective</span>
      <p>minimize <span class="mono">C(x) = −cut(x)</span></p>
      <span>More edges cut → lower cost</span>
    </div>
  </Panel>

  <Panel
    title="Benchmark results"
    subtitle={showExample ? 'Example data · not measured results' : 'No solver has run'}
    className="solver-panel"
  >
    {#key revision}<div
        class="solver-results"
        in:fade={{ duration: prefersReducedMotion.current ? 0 : 140 }}
      >
        <div class="solver-block">
          <div class="solver-label">
            <span class="solver-dot classical"></span>
            <h3>Classical baseline</h3>
          </div>
          <p class="solver-method">Brute force</p>
          <p class="solver-objective cyan-text">
            {showExample ? run.comparison.classical?.objective?.toFixed(2) : '—'}<span
              >{showExample ? 'example objective' : 'No result'}</span
            >
          </p>
          <div class="solver-detail"><span>Execution time</span><strong>Not measured</strong></div>
        </div>
        <div class="solver-block quantum">
          <div class="solver-label">
            <span class="solver-dot qaoa"></span>
            <h3>QAOA</h3>
          </div>
          <p class="solver-method">Quantum simulator integration pending</p>
          <p class="solver-objective violet-text">
            {showExample ? run.comparison.quantum?.objective?.toFixed(2) : '—'}<span
              >{showExample ? 'example best sample' : 'No result'}</span
            >
          </p>
          <div class="solver-detail"><span>Execution time</span><strong>Not measured</strong></div>
        </div>
        <div class="gap-note">
          <Icon name="info" size={14} />
          <p>
            {showExample
              ? 'Example objectives illustrate the display. They are not solver output.'
              : 'Load example data to inspect these result displays.'}
          </p>
        </div>
      </div>{/key}
  </Panel>
</div>

<p class="run-status" role="status"><Icon name="check" size={13} />{status}</p>

<div class="charts-grid" id="benchmark-results">
  <Panel
    title="QAOA objective trace"
    subtitle={showExample
      ? 'Example data · 16 illustrative points, not optimizer evaluations'
      : 'No optimizer trace available'}
  >
    {#snippet toolbar()}<div class="segmented">
        <button
          class:selected={chartTab === 'expected'}
          aria-pressed={chartTab === 'expected'}
          onclick={() => (chartTab = 'expected')}>Expected</button
        ><button
          class:selected={chartTab === 'sampled'}
          aria-pressed={chartTab === 'sampled'}
          onclick={() => (chartTab = 'sampled')}>Best sampled</button
        >
      </div>{/snippet}
    {#if showExample}<LineChart
        values={chartTab === 'expected' ? run.expected : run.bestSampled}
        optimum={-graph.optimumCut}
      />{:else}<div class="result-empty">
        No optimization has been executed. Load example data to inspect the chart.
      </div>{/if}
  </Panel>
  <Panel
    title="Cut-size distribution"
    subtitle={showExample
      ? 'Example data · illustrative counts, not measurements'
      : 'No measurement samples available'}
    >{#if showExample}<Histogram bins={run.histogram} />{:else}<div class="result-empty">
        No measurement samples have been collected.
      </div>{/if}</Panel
  >
</div>

<Panel title="Execution metrics" className="record-panel">
  <div class="record-grid">
    <div>
      <span class="eyebrow">Circuit depth</span><strong class="unavailable">Not measured</strong>
    </div>
    <div>
      <span class="eyebrow">Measurement shots</span><strong class="unavailable"
        >Not collected</strong
      >
    </div>
    <div>
      <span class="eyebrow">Simulator execution time</span><strong class="unavailable"
        >Not measured</strong
      >
    </div>
    <div>
      <span class="eyebrow">Data source</span><strong class="source"
        >{showExample ? 'Example data only' : 'No results'}</strong
      >
    </div>
  </div>
  <details class="run-details">
    <summary>Inspect data & integration notes<Icon name="plus" size={15} /></summary>
    <div class="details-content">
      <p>
        Optional example data demonstrates objectives, chart points, and count displays. Execution
        time, circuit depth, and optimizer evaluation counts are not measured and remain
        unavailable. Control values preview a request; they are not a run record.
      </p>
      <p>
        The shared API contracts define request validation, structured errors, x[0]-first
        bitstrings, and explicit timing scopes. Solver execution remains unimplemented; no timing
        decomposition or speedup is inferred here.
      </p>
      {#if showExample}<div class="table-scroll">
          <table>
            <caption>Underlying example trace and sample distribution</caption><thead
              ><tr><th>Example point</th><th>Expected cost</th><th>Best sampled cost</th></tr
              ></thead
            ><tbody
              >{#each run.expected as value, i}<tr
                  ><td>{i + 1}</td><td>{value.toFixed(2)}</td><td
                    >{run.bestSampled[i].toFixed(2)}</td
                  ></tr
                >{/each}</tbody
            >
          </table>
          <table>
            <thead><tr><th>Cut size</th><th>Count</th></tr></thead><tbody
              >{#each run.histogram as bin}<tr><td>{bin.cut}</td><td>{bin.count}</td></tr
                >{/each}</tbody
            >
          </table>
        </div>{/if}
    </div>
  </details>
</Panel>

<style>
  .result-empty {
    min-height: 195px;
    display: grid;
    align-content: center;
    padding: 24px;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
    border-top: 1px solid var(--border);
  }
  #experiment-settings,
  #benchmark-results {
    scroll-margin-top: 24px;
  }
  .optimization-intro {
    display: grid;
    grid-template-columns: minmax(0, 1.65fr) minmax(280px, 1fr);
    gap: 23px;
    align-items: start;
    margin-top: 23px;
  }
  .lab-introduction {
    min-width: 0;
  }
  .lab-description {
    padding: 22px 2px 0;
  }
  .lab-description h2 {
    margin: 0 0 9px;
    font-size: 15px;
    font-weight: 500;
    letter-spacing: normal;
  }
  .lab-description > p {
    margin: 0;
    font-size: 12px;
    line-height: 1.85;
    color: var(--muted);
    max-width: 710px;
  }
  .experiment-context {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    margin: 27px 0 17px;
  }
  .experiment-context > div {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .context-rule {
    width: 16px;
    height: 2px;
    background: var(--cyan);
  }
  .experiment-context h2 {
    font-size: 13px;
    font-weight: 500;
    margin: 0;
  }
  .context-separator {
    color: var(--border);
    font-size: 12px;
  }
  .context-detail {
    color: var(--muted);
    font-size: 12px;
  }
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 13px;
    margin-bottom: 22px;
  }
  .lab-grid {
    display: grid;
    grid-template-columns: 230px minmax(0, 1fr) 250px;
    gap: 17px;
    align-items: start;
  }
  .controls-form {
    padding: 0 21px 20px;
  }
  .controls-form > label,
  .range-heading > label,
  legend {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    color: var(--muted);
    font-size: 12px;
    margin: 0 0 9px;
  }
  input[type='number'],
  select {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    background: var(--surface);
    min-height: 35px;
    font-size: 12px;
    padding: 8px 10px;
    margin-bottom: 19px;
  }
  select {
    padding-right: 21px;
  }
  input[type='number'] {
    font-family: var(--mono);
  }
  .control-divider {
    border-top: 1px solid var(--border);
    margin: 2px 0 20px;
  }
  .range-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 9px;
  }
  .range-heading label {
    margin: 0;
  }
  output {
    color: var(--blue-light);
    font: 12px var(--mono);
  }
  input[type='range'] {
    width: 100%;
    height: 3px;
    display: block;
    margin: 12px 0 8px;
    accent-color: var(--accent);
    cursor: pointer;
  }
  .range-labels {
    display: flex;
    justify-content: space-between;
    color: var(--muted);
    font: 12px var(--mono);
    margin-bottom: 20px;
  }
  fieldset {
    margin: 0 0 20px;
    border: none;
    padding: 0;
  }
  legend {
    padding: 0;
  }
  .shot-options {
    display: flex;
    gap: 5px;
  }
  .shot-options label {
    border-radius: 4px;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
    flex: 1;
    font: 12px var(--mono);
    color: var(--muted);
    min-height: 31px;
    border: 1px solid var(--border);
    background: var(--surface-raised);
    cursor: pointer;
  }
  .shot-options label.selected {
    border-color: var(--accent);
    background: var(--surface);
    color: var(--accent);
  }
  .shot-options input {
    position: absolute;
    opacity: 0;
    width: 100%;
    height: 100%;
    cursor: pointer;
    margin: 0;
  }
  .shot-options label:focus-within {
    outline: 2px solid var(--blue-light);
    outline-offset: 2px;
  }
  .backend-preview {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 0 19px;
    color: var(--blue);
  }
  .backend-preview strong {
    display: block;
    font-size: 12px;
    font-weight: 400;
    color: var(--text);
    margin-bottom: 4px;
  }
  .backend-preview span {
    display: block;
    font-size: 12px;
    color: var(--muted);
  }
  .load-button {
    width: 100%;
    font-size: 12px;
  }
  .control-note {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.7;
    margin: 12px 0 0;
  }
  .objective-strip {
    padding: 17px 21px 19px;
    border-top: 1px solid var(--border);
  }
  .objective-strip .eyebrow {
    font-size: 12px;
  }
  .objective-strip p {
    font-size: 12px;
    margin: 8px 0;
    color: var(--muted);
  }
  .objective-strip .mono {
    color: var(--blue);
    margin-left: 5px;
    font-size: 12px;
  }
  .objective-strip > span {
    color: var(--muted);
    font-size: 12px;
  }
  .solver-results {
    padding: 0 20px;
  }
  .solver-block {
    padding: 5px 0 22px;
  }
  .solver-block.quantum {
    border-top: 1px solid var(--border);
    padding-top: 22px;
  }
  .solver-label {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .solver-label h3 {
    font-size: 12px;
    font-weight: 500;
    margin: 0;
  }
  .solver-dot {
    width: 5px;
    height: 5px;
    display: inline-block;
  }
  .solver-dot.classical {
    background: var(--cyan);
  }
  .solver-dot.qaoa {
    background: var(--violet);
  }
  .solver-label :global(.badge) {
    margin-left: auto;
    padding: 3px 5px;
    font-size: 12px;
  }
  .solver-method {
    margin: 6px 0 17px 12px;
    color: var(--muted);
    font-size: 12px;
  }
  .solver-objective {
    font: 31px/1 var(--mono);
    letter-spacing: normal;
    margin: 0 0 16px 10px;
    display: flex;
    align-items: baseline;
    gap: 11px;
  }
  .solver-objective > span {
    font: 12px var(--mono);
    letter-spacing: normal;
    color: var(--muted);
  }
  .solver-detail {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin: 0 0 0 12px;
    font-size: 12px;
    color: var(--muted);
  }
  .solver-detail strong {
    font: 12px var(--mono);
    color: var(--text);
  }
  .gap-note {
    padding: 15px 0;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    color: var(--muted);
    border-top: 1px solid var(--border);
  }
  .gap-note p {
    margin: 0;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.75;
  }
  .run-status {
    margin: 13px 0 23px;
    display: flex;
    gap: 7px;
    align-items: flex-start;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.5;
  }
  .run-status :global(svg) {
    color: var(--success);
  }
  .charts-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
    gap: 20px;
    margin-bottom: 22px;
  }
  .charts-grid :global(.panel-heading) {
    gap: 10px;
  }
  .charts-grid .segmented button {
    font-size: 12px;
    padding-inline: 8px;
  }
  .record-grid {
    padding: 6px 24px 25px;
    display: grid;
    grid-template-columns: 1fr 1fr 1.2fr 1.5fr;
    gap: 20px;
  }
  .record-grid > div {
    border-left: 1px solid var(--border);
    padding-left: 20px;
  }
  .record-grid > div:first-child {
    padding: 0;
    border: 0;
  }
  .record-grid .eyebrow {
    font-size: 12px;
  }
  .record-grid strong {
    display: block;
    font: 20px var(--mono);
    margin-top: 12px;
    color: var(--text);
  }
  .record-grid .unavailable,
  .record-grid .source {
    font:
      12px 'IBM Plex Sans',
      sans-serif;
    color: var(--muted);
    margin-top: 18px;
  }
  .run-details {
    border-top: 1px solid var(--border);
  }
  summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    cursor: pointer;
    color: var(--text);
    font-size: 12px;
    list-style: none;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  .details-content {
    padding: 0 24px 24px;
  }
  .details-content p {
    font-size: 12px;
    line-height: 1.8;
    color: var(--muted);
    max-width: 850px;
  }
  .table-scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font: 12px var(--mono);
  }
  td,
  th {
    padding: 9px 10px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    color: var(--muted);
  }
  th {
    color: var(--text);
    font-weight: 400;
  }
  caption {
    text-align: left;
    color: var(--muted);
    padding: 12px 10px;
    font-family: 'IBM Plex Sans', sans-serif;
  }
  .qubo-toolbar {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: center;
    padding: 10px 18px;
    background: var(--surface-raised);
    border-top: 1px solid var(--border);
  }
  .qubo-toolbar .eyebrow {
    font-size: 12px;
  }
  .qubo-toolbar .button {
    font-size: 12px;
  }
  .qubo-view .code-block {
    height: 322px;
    font-size: 12px;
  }
  .qubo-view > p {
    padding: 13px 20px;
    margin: 0;
    font-size: 12px;
    line-height: 1.6;
    color: var(--muted);
    border-top: 1px solid var(--border);
  }
  @media (min-width: 1600px) {
    .lab-grid {
      grid-template-columns: 255px minmax(0, 1fr) 280px;
    }
  }
  @media (max-width: 1300px) {
    .lab-grid {
      grid-template-columns: 215px minmax(0, 1fr);
    }
    :global(.solver-panel) {
      grid-column: 1 / -1;
    }
    .solver-results {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 24px;
    }
    .solver-block.quantum {
      border-top: 0;
      border-left: 1px solid var(--border);
      padding: 5px 0 22px 24px;
    }
    .gap-note {
      border-top: 0;
      padding-top: 4px;
    }
    .charts-grid {
      grid-template-columns: 1.4fr 1fr;
    }
    .charts-grid :global(.panel-heading) {
      flex-wrap: wrap;
    }
  }
  @media (max-width: 800px) {
    .optimization-intro {
      grid-template-columns: 1fr;
    }
    .metrics-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    .lab-grid {
      grid-template-columns: 200px minmax(0, 1fr);
      gap: 13px;
    }
    .controls-form {
      padding-inline: 17px;
    }
    :global(.problem-panel .panel-heading) {
      flex-wrap: wrap;
    }
    .charts-grid {
      grid-template-columns: 1fr;
    }
    .record-grid {
      grid-template-columns: 1fr 1fr;
      gap: 25px;
    }
    .record-grid > div:nth-child(3) {
      border: 0;
      padding: 0;
    }
    .solver-results {
      grid-template-columns: 1fr 1fr;
      gap: 15px;
    }
    .gap-note {
      grid-column: 1 / -1;
      padding: 0 0 12px;
    }
  }
  @media (max-width: 550px) {
    .lab-grid {
      grid-template-columns: 1fr;
    }
    .controls-form {
      display: block;
    }
    .experiment-context {
      flex-wrap: wrap;
    }
    .context-detail {
      font-size: 12px;
    }
    .experiment-context :global(.badge) {
      font-size: 12px;
    }
    .metrics-grid {
      gap: 10px;
    }
    :global(.controls-panel) {
      order: 0;
    }
    .solver-results {
      padding-inline: 18px;
    }
    .solver-objective {
      font-size: 27px;
      margin-left: 0;
    }
    .solver-objective > span {
      font-size: 12px;
    }
    .solver-detail {
      flex-wrap: wrap;
      margin-left: 0;
    }
    .solver-block.quantum {
      padding-left: 15px;
    }
    .record-grid {
      padding-inline: 18px;
    }
  }
</style>
