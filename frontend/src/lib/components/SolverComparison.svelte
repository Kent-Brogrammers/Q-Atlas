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
    color: #63738a;
    font-size: 12px;
  }
  i {
    display: inline-block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #5eade9;
  }
  i.qaoa {
    background: #a38cc6;
  }
  strong {
    font: 400 13px var(--mono);
    color: #344760;
  }
  strong small {
    font-size: 12px;
    font-weight: 400;
    color: #687382;
    margin-left: 5px;
  }
  .comparison-track {
    height: 10px;
    background: #f0f5fb;
    border-radius: 4px;
    overflow: hidden;
  }
  .comparison-track > span {
    height: 100%;
    display: block;
    background: #7cbaec;
    border-radius: 4px;
    transition: width 0.15s;
  }
  .comparison-track > span.qaoa {
    background: #b6a3d8;
  }
  .comparison-foot {
    margin-top: 22px;
    padding-top: 15px;
    border-top: 1px solid #edf1f7;
  }
  .comparison-foot p {
    font-size: 12px;
    line-height: 1.65;
    color: #677383;
    margin: 4px 0 0;
  }
</style>
