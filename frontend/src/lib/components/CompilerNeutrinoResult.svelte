<script lang="ts">
  import { untrack } from 'svelte';
  import type { NeutrinoResponse } from '../../types/index.ts';
  import { neutrinoTimings } from '../presentation/neutrinos.ts';
  import { duration } from '../presentation/format.ts';
  import Metric from './Metric.svelte';
  import Chart from './NeutrinoProbabilityChart.svelte';
  let { result }: { result: NeutrinoResponse } = $props();
  let index = $state(untrack(() => Math.floor(result.results.length / 2)));
  const pct = (p: number) => `${(p * 100).toFixed(2)}%`;
  let timings = $derived(neutrinoTimings(result.results));
</script>

<div class="compiler-neutrino-result">
  <p><strong>Neutrino simulation completed · local Aer simulation</strong></p>
  <p>
    The same {result.results.length} input points are evaluated by SciPy and the compiled one-qubit circuit.
    Both calculate flavor probabilities; the circuit also collects finite-shot measurements.
  </p>
  <div class="metrics">
    <Metric
      label="Classical probability calculation"
      value={duration(timings.classicalMs)}
      note="Sum of SciPy reference timers across this curve"
    />
    <Metric
      label="Circuit workflow on this computer"
      value={duration(timings.circuitMs)}
      note="Build, transpile, ideal simulation and shot sampling; summed across points"
    />
    <Metric
      label="Ideal circuit execution only"
      value={duration(timings.idealMs)}
      note="Included in circuit workflow; not additional time"
    />
  </div>
  <p>
    These are measured computation times, excluding browser/network time. The methods do different
    extra work; their ratio does not establish quantum speedup. Physical QPU usage appears
    separately for an actual hardware job.
  </p>
  <Chart {result} bind:index />
  <div class="table-scroll">
    <table>
      <caption>Conversion to the other flavor · same normalized inputs</caption>
      <thead
        ><tr
          ><th>{result.axis === 'potential' ? 'Matter potential' : 'Distance'}</th><th>Classical</th
          ><th>Ideal circuit</th><th>Measured shots</th><th>Ideal error</th><th>Classical time</th
          ><th>Circuit workflow</th></tr
        ></thead
      >
      <tbody
        >{#each result.results as point, i}<tr
            ><td>{result.coordinates[i].toFixed(4)}</td><td>{pct(point.numerical.other)}</td><td
              >{pct(point.ideal.other)}</td
            ><td>{pct(point.measured.other)}</td><td
              >{point.absolute_errors.ideal_vs_numerical.other.toExponential(2)}</td
            ><td>{duration(point.timing_ms.classical)}</td><td
              >{duration(point.timing_ms.circuit_end_to_end)}</td
            ></tr
          >{/each}</tbody
      >
    </table>
  </div>
</div>

<style>
  .compiler-neutrino-result {
    --lab-teal: var(--accent);
    --lab-border: var(--border);
    --lab-muted: var(--muted);
  }
  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
  }
  p {
    line-height: 1.7;
    font-size: 14px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  caption {
    text-align: left;
    padding: 12px 0;
  }
  td,
  th {
    text-align: left;
    padding: 12px;
    border-bottom: 1px solid var(--border);
  }
</style>
