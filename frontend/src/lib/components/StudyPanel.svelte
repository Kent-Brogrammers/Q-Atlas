<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import { api } from '../../api/client.ts';
  import {
    axes,
    downloadJson,
    planStudy,
    summarize,
    type Axis,
    type Experiment,
    type Requests,
    type StudyReport
  } from '../studies/model.ts';
  import { runStudy } from '../studies/runner.ts';
  import Panel from './Panel.svelte';
  import StudyChart from './StudyChart.svelte';
  let {
    experiment,
    request,
    disabled = false,
    running = $bindable(false)
  }: {
    running?: boolean;
    experiment: Experiment;
    request: Requests[Experiment] | null;
    disabled?: boolean;
  } = $props();
  let axis = $state<Axis>(untrack(() => axes[experiment][0].id));
  let valueText = $state(untrack(() => axes[experiment][0].values));
  let seedText = $state('42, 142, 242');
  let budget = $state(120);
  let report = $state<StudyReport | null>(null);
  let error = $state('');
  let progress = $state('');
  let selectedMetric = $state('');
  let controller: AbortController | undefined;
  let revision = 0;
  let key = $derived(JSON.stringify(request));
  let preview = $derived.by(() => {
    try {
      return request
        ? { plan: planStudy(experiment, request, axis, valueText, seedText, budget), error: '' }
        : { plan: null, error: 'Enter valid settings above to prepare a study.' };
    } catch (cause) {
      return { plan: null, error: cause instanceof Error ? cause.message : 'Invalid study.' };
    }
  });
  let summary = $derived(report ? summarize(report) : []);
  let keys = $derived([...new Set(summary.flatMap((row) => Object.keys(row.metrics)))]);
  $effect(() => {
    key;
    axis;
    valueText;
    seedText;
    budget;
    clear();
  });
  function clear() {
    revision++;
    controller?.abort();
    report = null;
    error = '';
    progress = '';
  }
  onDestroy(() => {
    revision++;
    controller?.abort();
  });
  function chooseAxis() {
    valueText = axes[experiment].find((item) => item.id === axis)!.values;
  }
  async function run() {
    if (running || !preview.plan) return;
    clear();
    const version = revision;
    running = true;
    controller = new AbortController();
    try {
      const clients = {
        compiler: api.compilerBenchmark,
        optimization: api.optimization,
        materials: api.materials,
        search: api.search,
        neutrinos: api.neutrinos
      };
      // The discriminant chooses the matching established typed transport.
      const execute = clients[experiment] as (
        r: Requests[Experiment],
        s: AbortSignal
      ) => Promise<import('../studies/model.ts').Results[Experiment]>;
      const measured = await runStudy(
        preview.plan,
        execute,
        controller.signal,
        (done, total) => {
          if (version === revision) progress = `${done} of ${total} requests recorded`;
        },
        navigator.userAgent
      );
      if (version === revision) {
        report = measured;
        selectedMetric =
          experiment === 'materials'
            ? 'Total observable error'
            : experiment === 'search'
              ? 'Measured success'
              : experiment === 'neutrinos'
                ? 'Mean total probability error'
                : 'Objective gap';
      }
    } catch (cause) {
      if (version === revision) error = cause instanceof Error ? cause.message : 'Study failed.';
    } finally {
      running = false;
    }
  }
  function format(value: number | null | undefined) {
    return value == null ? 'Unavailable' : Number(value.toPrecision(6)).toLocaleString();
  }
</script>

<Panel title="Parameter study" subtitle="Sequential local runs · complete raw evidence retained">
  <div class="study-body">
    <p>
      Choose a finite grid and distinct seeds. Other controls follow the settings above.
      {#if experiment === 'optimization'}A size study uses unit-weight cycle graphs at every size.{/if}
      {#if experiment === 'search'}A size study uses one explicit all-zero target and automatic
        iterations at every size.{/if}
      {#if experiment === 'materials'}Each request measures only the configured terminal time.{/if}
    </p>
    <fieldset disabled={running || disabled}>
      <div class="study-settings">
        <label
          >Vary<select bind:value={axis} onchange={chooseAxis}
            >{#each axes[experiment] as item}<option value={item.id}>{item.label}</option
              >{/each}</select
          ></label
        >
        <label>Values, comma separated<input bind:value={valueText} /></label>
        <label>Seeds, comma separated<input bind:value={seedText} /></label>
        <label
          >Suite budget (seconds)<input
            type="number"
            min="1"
            max="120"
            bind:value={budget}
          /></label
        >
      </div>
    </fieldset>
    <p class="note">
      {preview.plan
        ? `${preview.plan.points.length} requests · ${preview.plan.totalShots.toLocaleString()} final measurement shots · up to ${budget}s`
        : preview.error}
    </p>
    <div class="actions">
      <button class="button primary" disabled={running || disabled || !preview.plan} onclick={run}
        >{running ? 'Measuring study…' : 'Run selected study'}</button
      >
      {#if running}<button class="button" onclick={() => controller?.abort()}>Stop study</button
        >{/if}
      {#if report}<button
          class="button"
          onclick={() =>
            downloadJson(
              { ...JSON.parse(JSON.stringify(report)), summaries: summary },
              `q-atlas-${experiment}-study.json`
            )}>Download study JSON</button
        >{/if}
    </div>
    <p class="note" role="status">{progress}</p>
    {#if error}<p role="alert">{error}</p>{/if}
    {#if report}
      <p role="status">
        <strong
          >{report.status === 'completed'
            ? 'Live Aer study complete.'
            : 'Incomplete study.'}</strong
        >
        {report.records.filter((r) => r.status === 'completed').length} completed requests out of {report
          .plan.points.length} planned.
      </p>
      {#each report.records.filter((r) => r.status !== 'completed') as record}<p role="alert">
          Value {record.value}, seed {record.seed}: {record.error}
        </p>{/each}
      {#if summary.some((row) => row.count > 0)}
        <StudyChart
          rows={summary}
          metrics={['Classical reference (ms)', 'Circuit path (ms)']}
          label="Measured runtime by parameter"
        />
        {#if experiment === 'search' && report.plan.axis === 'size'}<StudyChart
            rows={summary}
            metrics={[
              'Oracle queries per attempt',
              'Classical expected queries',
              'Classical observed queries'
            ]}
            label="Oracle query counts by search size"
          />{/if}
        <label
          >Quality / resource metric<select bind:value={selectedMetric}
            ><option value="">Choose a metric</option
            >{#each keys.filter((k) => !k.endsWith('(ms)')) as name}<option value={name}
                >{name}</option
              >{/each}</select
          ></label
        >
        {#if selectedMetric}<StudyChart
            rows={summary}
            metrics={[selectedMetric]}
            label={selectedMetric}
          />{/if}
        <div class="table-scroll">
          <table>
            <caption>Completed-run statistics · observed ranges, not confidence intervals</caption
            ><thead
              ><tr
                ><th>Value</th><th>Runs</th><th>Metric</th><th>Samples</th><th>Median</th><th
                  >Minimum</th
                ><th>Maximum</th></tr
              ></thead
            ><tbody>
              {#each summary as row}{#each Object.entries(row.metrics) as [name, m]}<tr
                    ><td>{row.value}</td><td>{row.count}</td><td>{name}</td><td>{m.count}</td><td
                      >{format(m.median)}</td
                    ><td>{format(m.min)}</td><td>{format(m.max)}</td></tr
                  >{/each}{/each}
            </tbody>
          </table>
        </div>
      {/if}
    {/if}
    <p class="note">
      Ranges describe the selected seeds. Simulation and reference paths can perform different
      workloads; these timings do not establish quantum speedup. Stop prevents further requests and
      cancels browser waiting; backend workers retain their own time limits. Failed points stay in
      exports and are excluded from statistics.
    </p>
  </div>
</Panel>

<style>
  .study-body {
    padding: 0 22px 22px;
  }
  p {
    font-size: 13px;
    line-height: 1.7;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
  }
  .study-settings {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 14px;
  }
  label {
    display: grid;
    gap: 8px;
    font-size: 12px;
    color: var(--muted);
  }
  input,
  select {
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
    gap: 10px;
    flex-wrap: wrap;
  }
  .note {
    color: var(--muted);
    font-size: 12px;
  }
  table {
    width: 100%;
    font-size: 12px;
    border-collapse: collapse;
  }
  td,
  th {
    padding: 9px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }
  caption {
    text-align: left;
    padding: 10px 0;
    color: var(--muted);
  }
</style>
