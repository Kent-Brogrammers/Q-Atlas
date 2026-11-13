<script lang="ts">
  import type { HardwareJob } from '../../types/index.ts';
  import Metric from './Metric.svelte';
  import StudyChart from './StudyChart.svelte';
  import { duration } from '../presentation/format.ts';
  let { job }: { job: HardwareJob } = $props();
  let names = $derived([...new Set(job.metrics?.map((m) => m.name) ?? [])]);
  let providerTimes = $derived(job.shared_job_timings ?? job.timings);
  let selected = $state('');
  let selectedName = $derived(names.includes(selected) ? selected : names[0]);
  let rows = $derived(
    (job.metrics ?? [])
      .filter((m) => m.name === selectedName)
      .map((m, i) => ({
        value: m.coordinate ?? i,
        metrics: {
          Classical: { median: m.classical, min: m.classical, max: m.classical },
          'Physical QPU': { median: m.quantum, min: m.quantum, max: m.quantum }
        }
      }))
  );
  let timings = $derived([
    ['Classical reference', job.timings?.classical_ms],
    ['Local angle training', job.timings?.local_training_ms],
    ['Preparation (includes classical/training)', job.timings?.preparation_ms],
    ['Transpilation', job.timings?.transpilation_ms],
    ['Submission / network', job.timings?.submission_ms],
    ['Provider queue interval', job.timings?.provider_queue_ms],
    ['Provider RUNNING interval', job.timings?.provider_execution_ms],
    ['Result retrieval', job.timings?.retrieval_ms],
    ['Observed total wall time (includes polling delay)', job.timings?.observed_wall_ms]
  ] as const);
  const format = (value: number | null | undefined) =>
    value == null ? 'Unavailable' : Number(value.toPrecision(6)).toLocaleString();
</script>

<div class="hardware-analytics">
  <p class="evidence">
    <strong>Physical IBM QPU measurement</strong> · simulated: false · {job.backend_name} · {job.shots}
    shots per circuit
  </p>

  {#if names.length > 1}<label
      >Observable<select
        value={selectedName}
        onchange={(event) => (selected = event.currentTarget.value)}
        >{#each names as name}<option value={name}>{name}</option>{/each}</select
      ></label
    >{/if}
  {#if rows.length > 1}<StudyChart
      {rows}
      metrics={['Classical', 'Physical QPU']}
      label={selectedName ?? 'Measured comparison'}
      xLabel={job.task.kind === 'neutrinos'
        ? job.task.parameters.axis === 'potential'
          ? 'Matter potential (normalized)'
          : 'Distance (normalized)'
        : 'Time (dimensionless)'}
    />{/if}
  {#if job.metrics?.[0]}{@const m = job.metrics[0]}
    <div class="metrics">
      <Metric
        label="Classical answer"
        value={format(m.classical)}
        unit={m.unit}
        note="Independent reference for this input"
      /><Metric
        label="QPU measured answer"
        note="Computed from physical measurement counts"
        value={format(m.quantum)}
        unit={m.unit}
      /><Metric
        label="Difference"
        value={format(m.absolute_error)}
        unit={m.unit}
        note="Absolute error, or gap from the exact optimum"
      />
    </div>
    <p>
      <strong
        >{m.absolute_error === 0
          ? 'The measured result matches the classical reference.'
          : 'The measured result differs from the classical reference.'}</strong
      >
      {m.name}: classical {format(m.classical)}, QPU {format(m.quantum)} ({m.unit}).
      {#if job.task.kind === 'compiler' || job.task.kind === 'optimization'}Lower cost is better;
        this compares the best sampled assignment.{:else}The table below shows the error for every
        measured point.{/if}
    </p>
  {/if}
  {#if job.metrics?.length}<div class="table-scroll">
      <table>
        <caption>Same-instance classical and physical quantum results</caption><thead
          ><tr
            ><th>Quantity</th><th>Coordinate</th><th>Classical</th><th>QPU</th><th
              >Absolute error / gap</th
            ><th>Unit</th></tr
          ></thead
        ><tbody>
          {#each job.metrics ?? [] as m}<tr
              ><td>{m.name}</td><td>{format(m.coordinate)}</td><td>{format(m.classical)}</td><td
                >{format(m.quantum)}</td
              ><td>{format(m.absolute_error)}</td><td>{m.unit}</td></tr
            >{/each}
        </tbody>
      </table>
    </div>{/if}
  <details>
    <summary>Time &amp; circuit details · what each measurement includes</summary>
    <div class="metrics">
      <Metric
        label="Classical reference"
        value={duration(job.timings?.classical_ms)}
        note="Independent reference / exact solver"
      />
      <Metric
        label={job.shared_job_timings ? 'Shared job QPU usage' : 'Provider QPU usage'}
        value={format(providerTimes?.quantum_seconds)}
        unit="seconds"
        note={job.shared_job_timings
          ? 'Entire five-experiment job; not an individual runtime'
          : 'Provider-reported usage; excludes local training'}
      />
      <Metric
        label="Maximum circuit depth"
        value={format(Math.max(...(job.circuit_depths ?? [0])))}
        note={`${job.num_qubits} logical qubits · native transpiled circuits`}
      />
    </div>
    <div class="table-scroll">
      <table>
        <caption>Measured durations</caption><tbody
          >{#each timings as [name, value]}<tr><th>{name}</th><td>{duration(value)}</td></tr
            >{/each}</tbody
        >
      </table>
    </div>
  </details>
  <p class="note">
    {job.timing_note} Physical results include shot and device noise.
    {#if job.task.kind === 'materials'}Materials error also includes product-formula approximation.{/if}
    {#if job.task.kind === 'compiler' || job.task.kind === 'optimization'}QAOA trains angles locally
      before QPU sampling.{/if}
    {#if job.task.kind === 'search'}Search reports classical success 1 for a completed exact search;
      ideal Grover success and query counts are retained in the reference record.{/if}
  </p>
  <details>
    <summary>Raw counts, inputs, references, and package versions</summary>
    <pre>{JSON.stringify(job, null, 2)}</pre>
  </details>
</div>

<style>
  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
  }
  p {
    font-size: 13px;
    line-height: 1.7;
  }
  .note {
    color: var(--muted);
    font-size: 12px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin-top: 15px;
  }
  .table-scroll {
    overflow-x: auto;
  }
  td,
  th {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }
  caption {
    text-align: left;
    padding: 8px 0;
    color: var(--muted);
  }
  label {
    display: grid;
    gap: 8px;
    margin-top: 15px;
  }
  select {
    padding: 9px;
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
  }
  pre {
    max-height: 450px;
    overflow: auto;
    font-size: 12px;
  }
</style>
