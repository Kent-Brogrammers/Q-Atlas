<script lang="ts">
  import type { ExampleComparison } from '../types/examples.ts';
  let { result, optimum }: { result: ExampleComparison | null; optimum: number } = $props();
  let metric = $state<'quality' | 'time'>('quality');
  let rows = $derived([
    {
      label: 'Classical',
      value:
        metric === 'quality'
          ? result?.classical?.objective == null
            ? null
            : -result?.classical.objective
          : (result?.classical?.elapsed_ms ?? null)
    },
    {
      label: 'QAOA',
      value:
        metric === 'quality'
          ? result?.quantum?.objective == null
            ? null
            : -result?.quantum.objective
          : (result?.quantum?.elapsed_ms ?? null)
    }
  ]);
  let max = $derived(
    metric === 'quality' ? optimum : Math.max(1, ...rows.map((row) => row.value ?? 0))
  );
</script>

<div class="solver-comparison">
  <div class="comparison-top">
    <div class="segmented">
      <button
        class:selected={metric === 'quality'}
        aria-pressed={metric === 'quality'}
        onclick={() => (metric = 'quality')}>Solution quality</button
      ><button
        class:selected={metric === 'time'}
        aria-pressed={metric === 'time'}
        onclick={() => (metric = 'time')}>Execution time</button
      >
    </div>
  </div>
  <div class="comparison-bars">
    {#each rows as row, i}<div class="comparison-row">
        <div>
          <span><i class:qaoa={i === 1}></i>{row.label}</span><strong
            class:unavailable={row.value == null}
            >{row.value == null
              ? metric === 'time'
                ? 'Not measured'
                : 'No result'
              : row.value.toLocaleString()}{#if row.value != null}<small
                >{metric === 'quality' ? 'edges cut' : 'ms'}</small
              >{/if}</strong
          >
        </div>
        <div class="comparison-track">
          <span
            class:qaoa={i === 1}
            style:width={`${row.value == null ? 0 : (Math.max(0, row.value) / max) * 100}%`}
          ></span>
        </div>
      </div>{/each}
  </div>
  <div class="comparison-foot">
    <p>
      {metric === 'time'
        ? 'Timing is unavailable. No solver has been executed.'
        : result
          ? 'Example cut sizes only; not measured solver output.'
          : 'Load example data in Simulation settings to inspect solution quality displays.'}
    </p>
  </div>
</div>

<style>
  strong.unavailable {
    font: 400 12px var(--font-sans);
  }
  .solver-comparison {
    padding: 0 23px 20px;
  }
  .comparison-top {
    margin-bottom: 23px;
  }
  .segmented {
    display: flex;
  }
  .segmented button {
    flex: 1;
    font-size: 12px;
    padding-inline: 7px;
  }
  .comparison-bars {
    display: grid;
    gap: 19px;
  }
  .comparison-row > div:first-child {
    display: flex;
    justify-content: space-between;
    gap: 9px;
    align-items: center;
    margin-bottom: 9px;
  }
  .comparison-row > div:first-child > span {
    display: inline-flex;
    gap: 7px;
    align-items: center;
    color: var(--muted);
    font-size: 12px;
  }
  i {
    display: inline-block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--blue);
  }
  i.qaoa {
    background: var(--accent);
  }
  strong {
    font: 400 13px var(--mono);
    color: var(--text);
  }
  strong small {
    font-size: 12px;
    font-weight: 400;
    color: var(--muted);
    margin-left: 5px;
  }
  .comparison-track {
    height: 10px;
    background: var(--surface);
    border-radius: 4px;
    overflow: hidden;
  }
  .comparison-track > span {
    height: 100%;
    display: block;
    background: var(--blue);
    border-radius: 4px;
    transition: width 0.15s;
  }
  .comparison-track > span.qaoa {
    background: var(--accent);
  }
  .comparison-foot {
    margin-top: 22px;
    padding-top: 15px;
    border-top: 1px solid var(--border);
  }
  .comparison-foot p {
    font-size: 12px;
    line-height: 1.65;
    color: var(--muted);
    margin: 4px 0 0;
  }
</style>
