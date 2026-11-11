<script lang="ts">
  import type { RuntimeMeasurement } from '../../compiler/runtimes.ts';
  import { formatOptionalMs } from '../../compiler/source.ts';

  let { rows }: { rows: RuntimeMeasurement[] } = $props();
  let logarithmic = $state(true);
  const maximum = $derived(Math.max(0, ...rows.map((row) => row.milliseconds)));
  function width(milliseconds: number) {
    if (maximum === 0) return 0;
    return (
      100 *
      (logarithmic
        ? Math.log10(1 + milliseconds) / Math.log10(1 + maximum)
        : milliseconds / maximum)
    );
  }
</script>

<figure aria-label="Measured classical solve time and IBM QPU usage">
  <div class="chart-heading">
    <span>Measured time · milliseconds</span>
    <label><input type="checkbox" bind:checked={logarithmic} /> Log scale</label>
  </div>
  {#each rows as row (row.kind)}
    <div class="runtime-row">
      <div class="reading">
        <span>{row.label}</span><strong>{formatOptionalMs(row.milliseconds)}</strong>
      </div>
      <div class="track" aria-hidden="true">
        <div
          class="bar"
          class:qpu={row.kind === 'qpu'}
          style:width={`${width(row.milliseconds)}%`}
        ></div>
      </div>
    </div>
  {/each}
  <figcaption>
    {#if logarithmic}Bar lengths use log₁₀(1 + milliseconds) so small readings stay visible.
    {:else}Bar lengths are proportional to milliseconds.{/if}
    Classical time covers exact solving; QPU usage covers hardware sampling and its overhead. Local training
    and network time are excluded from the QPU bar. This is not an end-to-end speedup comparison.
  </figcaption>
</figure>

<style>
  figure {
    margin: 0;
    padding: 0 24px 20px;
  }
  .chart-heading,
  .reading {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
  }
  .chart-heading {
    margin-bottom: 24px;
    color: var(--muted);
    font-size: 12px;
  }
  label {
    display: inline-flex;
    gap: 8px;
    align-items: center;
  }
  .runtime-row + .runtime-row {
    margin-top: 22px;
  }
  .reading {
    margin-bottom: 10px;
    font-size: 13px;
  }
  strong {
    font: 400 13px var(--mono);
  }
  .track {
    height: 16px;
    background: var(--surface-raised);
    border-radius: 3px;
    overflow: hidden;
  }
  .bar {
    height: 100%;
    background: var(--blue);
    border-radius: 3px;
  }
  .bar.qpu {
    background: var(--accent, var(--blue));
  }
  figcaption {
    border-top: 1px solid var(--border);
    margin-top: 24px;
    padding-top: 14px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.7;
  }
  @media (max-width: 600px) {
    figure {
      padding-inline: 18px;
    }
  }
</style>
