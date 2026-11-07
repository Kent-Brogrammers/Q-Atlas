<script lang="ts">
  import { experiments } from '#lib/data/experiments.ts';
  import { graphs } from '#lib/data/fixtures.ts';
  import Icon from '#lib/components/Icon.svelte';
  import Panel from '#lib/components/Panel.svelte';
  import ExampleNotice from '#lib/components/ExampleNotice.svelte';
  import FeatureBanner from '#lib/components/FeatureBanner.svelte';
  import LibraryOverview from '#lib/components/LibraryOverview.svelte';
  let filter = $state<'all' | 'small'>('all');
  let visibleGraphs = $derived(
    graphs.filter((graph) => filter === 'all' || graph.nodes.length <= 6)
  );
</script>

<svelte:head><title>Overview · Q-Atlas</title></svelte:head>

<header class="page-heading">
  <div>
    <h1>Q-Atlas Overview</h1>
    <p>Experiment configuration, QUBO inspection, and benchmark comparisons.</p>
  </div>
  <a class="button small" href="/optimization/"
    >Open optimization<Icon name="northeast" size={15} /></a
  >
</header>
<ExampleNotice />

<div class="dashboard-columns grid gap-6">
  <div class="primary-column min-w-0">
    <FeatureBanner
      title="Quantum computing benchmarks"
      description="Configure small quantum computing problems and compare solution quality against classical baselines. Backend execution is not connected."
    >
      <a href="/optimization/">Max-Cut optimization<Icon name="arrow" size={15} /></a>
      <a href="/compiler/">Python compiler<Icon name="arrow" size={15} /></a>
    </FeatureBanner>

    <section class="experiment-modules" aria-labelledby="modules-heading">
      <div class="section-heading">
        <div>
          <h2 id="modules-heading">Experiments</h2>
          <p>Select a workspace to configure inputs and inspect available outputs.</p>
        </div>
      </div>
      <div class="module-grid grid grid-cols-1 gap-4 sm:grid-cols-2">
        {#each experiments as experiment}
          <a class="experiment-module {experiment.color}" href="/{experiment.id}/">
            <div class="module-top">
              <span class="module-icon"><Icon name={experiment.icon} size={21} /></span><Icon
                name="northeast"
                size={15}
              />
            </div>
            <h3>{experiment.title}</h3>
            <p>{experiment.description}</p>
            <div class="module-preview" aria-hidden="true">
              {#if experiment.id === 'compiler'}<span class="code-preview"
                  ><b>return</b> 3 − x[0] + 2*x[1]</span
                >
              {:else if experiment.id === 'materials'}<span class="spin-preview"
                  ><i>↑</i><span></span><i>↓</i><span></span><i>↑</i><span></span><i>↓</i></span
                >
              {:else if experiment.id === 'optimization'}<svg viewBox="0 0 220 35" fill="none"
                  ><path
                    d="M15 18 62 8l48 20 48-20 47 10M15 18l95 10 95-10M62 8h96"
                    stroke="#bed6f3"
                  /><g fill="#eaf3ff" stroke="#75a9e0"
                    ><circle cx="15" cy="18" r="5" /><circle cx="62" cy="8" r="5" /><circle
                      cx="110"
                      cy="28"
                      r="5"
                    /><circle cx="158" cy="8" r="5" /><circle cx="205" cy="18" r="5" /></g
                  ></svg
                >
              {:else}<span class="search-preview"
                  >{#each Array.from({ length: 12 }) as _, i}<i class:marked={i === 7}
                    ></i>{/each}<span>Marked state</span></span
                >{/if}
            </div>
            <div class="module-footer">
              <span>Open {experiment.short.toLowerCase()}</span><Icon name="arrow" size={13} />
            </div>
          </a>
        {/each}
      </div>
    </section>

    <Panel
      title="Max-Cut graph presets"
      subtitle="Problem definitions for inspecting graphs and QUBOs."
    >
      {#snippet toolbar()}<div class="segmented">
          <button
            class:selected={filter === 'all'}
            aria-pressed={filter === 'all'}
            onclick={() => (filter = 'all')}>All presets</button
          ><button
            class:selected={filter === 'small'}
            aria-pressed={filter === 'small'}
            onclick={() => (filter = 'small')}>≤ 6 variables</button
          >
        </div>{/snippet}
      <div class="notebook-table">
        <table>
          <thead><tr><th>Problem</th><th>Variables</th><th>Edges</th><th>Source</th></tr></thead
          ><tbody
            >{#each visibleGraphs as graph}<tr
                ><td
                  ><span class="notebook-icon"><Icon name="graph" size={17} /></span>
                  <div><strong>{graph.name}</strong><small>Unweighted Max-Cut</small></div></td
                ><td>{graph.nodes.length}</td><td>{graph.edges.length}</td><td>Built-in preset</td
                ></tr
              >{/each}</tbody
          >
        </table>
      </div>
      <div class="notebook-footer">
        <span>Graph definitions only; no solver results</span><a
          class="text-link"
          href="/optimization/">Configure Max-Cut<Icon name="arrow" size={14} /></a
        >
      </div>
    </Panel>
  </div>

  <aside class="analytics-column" aria-label="Workspace analytics and context">
    <Panel title="Execution metrics"><LibraryOverview /></Panel>
    <Panel title="Execution context">
      <div class="execution-context">
        <div>
          <span class="context-icon"><Icon name="terminal" size={17} /></span>
          <p><strong>Planned simulator</strong><span>Qiskit Aer · integration pending</span></p>
        </div>
        <div>
          <span class="context-icon violet"><Icon name="circuit" size={17} /></span>
          <p><strong>Quantum hardware</strong><span>Not connected</span></p>
        </div>
        <div>
          <span class="context-icon gray"><Icon name="layers" size={17} /></span>
          <p><strong>Current data source</strong><span>Optional example charts</span></p>
        </div>
      </div>
      <div class="context-footer">
        <Icon name="info" size={13} />Simulation is distinct from hardware execution.
      </div>
    </Panel>
    <section class="requirements-card">
      <h2>Benchmark requirements</h2>
      <p>Measured results must identify the objective, backend, and timing scope.</p>
      <div>
        <span><Icon name="check" size={12} />Shared QUBO objective</span>
        <span><Icon name="check" size={12} />Classical baseline</span>
        <span><Icon name="check" size={12} />Separate simulator and optimizer timing</span>
      </div>
    </section>
  </aside>
</div>

<style>
  .dashboard-columns {
    grid-template-columns: minmax(0, 1.65fr) minmax(290px, 1fr);
    margin-top: 23px;
    align-items: start;
  }
  .primary-column,
  .analytics-column {
    display: grid;
    gap: 24px;
  }
  .section-heading {
    display: flex;
    justify-content: space-between;
    gap: 15px;
    align-items: center;
    margin: 0 1px 16px;
  }
  .section-heading h2 {
    font-size: 16px;
    font-weight: 500;
    letter-spacing: normal;
    margin: 0 0 5px;
  }
  .section-heading p {
    font-size: 12px;
    color: #6a727f;
    margin: 0;
  }
  .experiment-module {
    min-width: 0;
    border: 1px solid #e5ebf2;
    border-radius: 4px;
    background: white;
    padding: 19px 20px 0;
    display: block;
    transition:
      border-color 0.15s,
      transform 0.15s,
      box-shadow 0.15s;
  }
  .experiment-module:hover {
    background: #f7faff;
    border-color: #b8d4f1;
    box-shadow: none;
  }
  .experiment-module.cyan {
    background: #f7fbff;
    border-color: #d9e8f7;
  }
  .module-top > :global(svg) {
    margin-left: auto;
  }
  .module-top {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 13px;
  }
  .module-icon {
    width: 34px;
    height: 34px;
    border-radius: 4px;
    background: #ecf4ff;
    color: #4b94d8;
    display: grid;
    place-items: center;
  }
  .violet .module-icon {
    background: #f4effb;
    color: #a18ac5;
  }
  .teal .module-icon {
    background: #edf8f7;
    color: #72a9a3;
  }
  .module-top > :global(svg) {
    color: #b0bdcd;
  }
  h3 {
    font-size: 15px;
    font-weight: 500;
    margin: 0 0 6px;
    letter-spacing: normal;
  }
  .experiment-module > p {
    font-size: 12px;
    line-height: 1.65;
    color: #687281;
    margin: 0;
    max-width: 260px;
  }
  .module-preview {
    height: 46px;
    display: flex;
    align-items: center;
    margin: 9px 0 8px;
  }
  .code-preview {
    display: block;
    background: #f5f8fc;
    border-radius: 4px;
    color: #6c84a5;
    font: 12px var(--mono);
    padding: 10px;
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
  }
  .code-preview b {
    color: #9b87bd;
    font-weight: 400;
  }
  .spin-preview {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0 5px;
  }
  .spin-preview i {
    width: 27px;
    height: 27px;
    display: grid;
    place-items: center;
    border: 1px solid #e0d5ee;
    border-radius: 50%;
    background: #f7f3fc;
    color: #ad97cb;
    font: 17px sans-serif;
  }
  .spin-preview > span {
    flex: 1;
    height: 1px;
    background: #e3dced;
  }
  .module-preview > svg {
    width: 100%;
    max-height: 38px;
  }
  .search-preview {
    display: flex;
    align-items: center;
    gap: 3px;
    flex-wrap: wrap;
  }
  .search-preview i {
    width: 9px;
    height: 20px;
    border-radius: 3px;
    background: #eaf2f5;
  }
  .search-preview i.marked {
    background: #8bc6c5;
  }
  .search-preview > span {
    color: #94a9ae;
    font-size: 12px;
    margin-left: 5px;
  }
  .module-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    border-top: 1px solid #edf1f6;
    margin: 0 -20px;
    padding: 12px 20px;
    color: #637389;
    font-size: 12px;
  }
  .cyan .module-footer {
    color: #3475b4;
  }
  .notebook-table {
    overflow-x: auto;
    padding: 0 23px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 12px;
  }
  th {
    padding: 10px 8px;
    color: var(--muted);
    background: #fafbfd;
    font-size: 12px;
    font-weight: 400;
  }
  th:first-child {
    padding-left: 11px;
    border-radius: 4px 0 0 4px;
  }
  th:last-child {
    border-radius: 0 4px 4px 0;
  }
  td {
    padding: 15px 8px;
    color: var(--muted);
    border-bottom: 1px solid #edf1f6;
  }
  td:nth-child(2),
  td:nth-child(3) {
    font-family: var(--mono);
  }
  td:first-child {
    display: flex;
    align-items: center;
    gap: 11px;
  }
  tr:last-child td {
    border-bottom: 0;
  }
  .notebook-icon {
    display: grid;
    place-items: center;
    width: 31px;
    height: 31px;
    background: #f1f6fc;
    border-radius: 4px;
    color: #87a9d2;
  }
  td strong {
    display: block;
    font-weight: 500;
    font-size: 12px;
    color: #4b6080;
    margin-bottom: 3px;
    white-space: nowrap;
  }
  td small {
    font-size: 12px;
    color: #69727e;
  }
  .notebook-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    padding: 15px 23px;
    border-top: 1px solid #edf1f6;
  }
  .notebook-footer > span {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: #68727e;
    font-size: 12px;
  }
  .notebook-footer .text-link {
    font-size: 12px;
  }
  .execution-context {
    display: grid;
    gap: 19px;
    padding: 1px 23px 23px;
  }
  .execution-context > div {
    display: flex;
    align-items: center;
    gap: 11px;
  }
  .context-icon {
    display: grid;
    place-items: center;
    width: 33px;
    height: 33px;
    border-radius: 4px;
    color: #6da2d3;
    background: #eef6ff;
  }
  .context-icon.violet {
    color: #a28bc4;
    background: #f7f2fc;
  }
  .context-icon.gray {
    color: #9aaabe;
    background: #f4f7fa;
  }
  .execution-context p {
    margin: 0;
  }
  .execution-context strong {
    display: block;
    font-size: 12px;
    color: #5c708c;
    font-weight: 500;
    margin-bottom: 4px;
  }
  .execution-context p > span {
    color: #677280;
    font-size: 12px;
  }
  .context-footer {
    display: flex;
    align-items: flex-start;
    gap: 7px;
    padding: 15px 23px;
    border-top: 1px solid #edf1f6;
    color: #697380;
    font-size: 12px;
    line-height: 1.5;
  }
  .requirements-card {
    padding: 24px;
    background: #f3f9ff;
    border: 1px solid #dfedfa;
    border-radius: 4px;
  }
  .requirements-card h2 {
    font-size: 20px;
    line-height: 1.35;
    letter-spacing: normal;
    font-weight: 500;
    color: #3a608a;
    margin: 10px 0;
  }
  .requirements-card p {
    color: #637385;
    font-size: 12px;
    line-height: 1.8;
    margin: 0 0 20px;
  }
  .requirements-card > div {
    display: grid;
    gap: 10px;
  }
  .requirements-card > div > span {
    color: #5c738c;
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    gap: 7px;
  }
  @media (min-width: 1650px) {
    .dashboard-columns {
      grid-template-columns: minmax(0, 1.65fr) minmax(290px, 1fr);
    }
  }
  @media (max-width: 1200px) {
    .dashboard-columns {
      grid-template-columns: minmax(0, 1fr) 280px;
      gap: 20px;
    }
    .experiment-module {
      padding-inline: 17px;
    }
    .module-footer {
      margin-inline: -17px;
      padding-inline: 17px;
    }
  }
  @media (max-width: 900px) {
    .dashboard-columns {
      grid-template-columns: 1fr;
    }
    .analytics-column {
      display: grid;
      grid-template-columns: 1fr 1fr;
      align-items: start;
    }
    .requirements-card {
      grid-column: 1 / -1;
    }
  }
  @media (max-width: 550px) {
    .analytics-column {
      grid-template-columns: 1fr;
    }
    .notebook-footer {
      align-items: flex-start;
      flex-direction: column;
    }
    :global(.notebook-table) {
      padding-inline: 13px;
    }
  }
</style>
