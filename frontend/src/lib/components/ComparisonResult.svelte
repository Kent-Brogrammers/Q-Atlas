<script lang="ts">
  import type { CompilerBenchmarkResult, OptimizationResult } from '../../types/index.ts';
  import Metric from './Metric.svelte';
  let { result }: { result: CompilerBenchmarkResult | OptimizationResult } = $props();
  const format = (value: number | null | undefined) =>
    value == null ? 'Unavailable' : Number(value.toPrecision(6)).toLocaleString();
</script>

<div class="comparison-result">
  <p>
    <strong>Live local Aer measurement</strong> · {result.metrics.num_qubits} qubits · {result
      .metadata.config.p} layers · {result.metrics.shots} shots · seed {result.metadata.seed}
  </p>
  <div class="metrics">
    <Metric
      label="Exact optimum"
      value={format(result.classical?.objective)}
      note={result.classical?.best_bitstring ?? 'No assignment'}
    />
    <Metric
      label="QAOA best sample"
      value={format(result.quantum?.objective)}
      note={result.quantum?.best_bitstring ?? 'No assignment'}
    />
    <Metric
      label="Objective gap"
      value={format(result.metrics.optimality_gap)}
      note="Sampled objective minus exact optimum"
    />
    <Metric
      label="Circuit depth"
      value={format(result.metrics.circuit_depth)}
      note={`${result.metrics.optimizer_evaluations ?? 'Unknown'} optimizer evaluations`}
    />
  </div>
  <div class="table-scroll">
    <table>
      <caption>Measured wall-clock milliseconds · declared solver scopes</caption><thead
        ><tr
          ><th>Method</th><th>Total</th><th>Optimizer</th><th>Transpilation</th><th>Sampling</th
          ></tr
        ></thead
      ><tbody>
        {#each [result.classical, result.quantum] as solver}{#if solver}<tr
              ><td>{solver.algorithm}</td><td>{format(solver.elapsed_ms)}</td><td
                >{format(solver.timing.optimizer_ms)}</td
              ><td>{format(solver.timing.transpilation_ms)}</td><td
                >{format(solver.timing.sampling_ms)}</td
              ></tr
            >{/if}{/each}
      </tbody>
    </table>
  </div>
  <p class="note">
    Canonical objective: minimize. API assignments list x[0] first. QAOA is trained with ideal
    statevector expectations, then sampled. Both methods run on the CPU; the sample gap accompanies
    runtime. Nested timers can overlap. Source analysis and graph conversion precede solver timers.
  </p>
  <details>
    <summary>Complete result and provenance</summary>
    <pre>{JSON.stringify(result, null, 2)}</pre>
  </details>
</div>

<style>
  .comparison-result {
    margin: 18px 0;
  }
  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
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
    font-size: 13px;
  }
  td,
  th {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }
  caption {
    text-align: left;
    padding: 15px 0;
    color: var(--muted);
  }
  pre {
    max-height: 400px;
    overflow: auto;
    font-size: 12px;
  }
</style>
