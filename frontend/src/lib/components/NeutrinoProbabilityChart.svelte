<script lang="ts">
  import type { ProposedNeutrinoResult } from '../neutrinos/proposal.ts';
  import { displaySeries, formatValue, probabilityPath } from '../neutrinos/presentation.ts';

  let {
    result = null,
    distanceKm = 0
  }: { result?: ProposedNeutrinoResult | null; distanceKm?: number } = $props();
  let source = $state<'both' | 'classical' | 'qiskit'>('both');
  let series = $derived(displaySeries(result));
  let extent = $derived(
    result?.distances_km.at(-1) ?? (Number.isFinite(distanceKm) && distanceKm >= 0 ? distanceKm : 0)
  );
  const colors = ['var(--blue)', 'var(--accent)', 'var(--success)'];
</script>

<div class="probability-chart">
  <div class="chart-controls">
    <div class="segmented" aria-label="Probability data source">
      {#each [['both', 'Both methods'], ['classical', 'Classical'], ['qiskit', 'Qiskit']] as [value, label]}
        <button
          class:selected={source === value}
          aria-pressed={source === value}
          disabled={!series.length}
          onclick={() => (source = value as typeof source)}>{label}</button
        >
      {/each}
    </div>
    <span class="chart-state">{series.length ? 'Simulator result' : 'No result data'}</span>
  </div>
  <figure>
    <div class="plot-region">
      <!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard users must be able to scroll this overflow region.) -->
      <div
        class="plot-scroll"
        tabindex="0"
        role="region"
        aria-label="Flavor probability plot; scroll horizontally on narrow screens"
      >
        <svg
          viewBox="0 0 860 330"
          role="img"
          aria-label={series.length
            ? 'Backend flavor probabilities by propagation distance.'
            : 'Empty probability axes. No experiment results available; no flavor curves are plotted.'}
        >
          <title>Flavor probability versus propagation distance</title>
          {#each [0, 0.25, 0.5, 0.75, 1] as value}
            <line
              x1="64"
              x2="818"
              y1={272 - value * 230}
              y2={272 - value * 230}
              stroke="var(--border)"
            />
            <text x="49" y={276 - value * 230} text-anchor="end">{value}</text>
          {/each}
          <text x="64" y="22" class="axis-title">Flavor probability</text>
          <line x1="64" x2="64" y1="42" y2="272" stroke="var(--border)" />
          <line x1="64" x2="818" y1="272" y2="272" stroke="var(--border)" />
          {#each extent > 0 ? [0, 0.25, 0.5, 0.75, 1] : [0] as fraction}
            <text x={64 + fraction * 754} y="295" text-anchor="middle"
              >{formatValue(fraction * extent, 1)}</text
            >
          {/each}
          <text x="818" y="320" text-anchor="end" class="axis-title">Propagation distance (km)</text
          >
          {#each series as item, i}
            {#if source !== 'qiskit'}<path
                d={probabilityPath(result!.distances_km, item.values.classical, extent)}
                stroke={colors[i % colors.length]}
                stroke-width="2"
                fill="none"><title>{item.flavor.label} · classical reference</title></path
              >{/if}
            {#if source !== 'classical'}<path
                d={probabilityPath(result!.distances_km, item.values.qiskit, extent)}
                stroke={colors[i % colors.length]}
                stroke-width="2"
                stroke-dasharray="6 4"
                fill="none"><title>{item.flavor.label} · Qiskit simulator</title></path
              >{/if}
          {/each}
        </svg>
      </div>
      {#if !series.length}<div class="plot-empty">
          <h3>No experiment results available</h3>
          <p>
            Flavor curves will appear after a supported model returns classical and Qiskit
            probabilities.
          </p>
        </div>{/if}
    </div>
    <figcaption>
      {#if series.length}<div class="flavor-legend">
          {#each series as item, i}<span
              ><i style:background={colors[i % colors.length]}></i>{item.flavor.symbol} · {item
                .flavor.label}</span
            >{/each}
        </div>
        <p>Solid: classical reference · Dashed: Qiskit simulator</p>
      {:else}<p>
          No flavor channels assumed. The propagation grid awaits backend configuration; axes are
          not simulation data.
        </p>{/if}
      <p class="mobile-scroll-note">
        Scroll the plot horizontally to inspect the full distance axis.
      </p>
    </figcaption>
  </figure>
</div>

<style>
  .chart-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 0 24px 20px;
    flex-wrap: wrap;
  }
  .chart-state {
    font-size: 12px;
    color: var(--muted);
  }
  figure {
    margin: 0;
  }
  .plot-region {
    position: relative;
    border-top: 1px solid var(--border);
    background: var(--surface-raised);
  }
  .plot-scroll {
    overflow-x: auto;
    padding: 14px 14px 0 0;
  }
  svg {
    width: 100%;
    min-width: 560px;
    display: block;
  }
  text {
    font: 12px var(--mono);
    fill: var(--muted);
  }
  .axis-title {
    font-family: var(--font-sans);
    font-size: 13px;
  }
  .plot-empty {
    position: absolute;
    inset: 34px 30px 64px 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    text-align: center;
    padding: 20px;
    pointer-events: none;
  }
  h3 {
    margin: 0 0 8px;
    font-size: 16px;
    font-weight: 500;
  }
  .plot-empty p {
    margin: 0;
    max-width: 370px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
  }
  figcaption {
    padding: 16px 24px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
  }
  figcaption p {
    margin: 0;
  }
  .flavor-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 8px;
  }
  .flavor-legend span {
    display: inline-flex;
    gap: 7px;
    align-items: center;
  }
  .mobile-scroll-note {
    display: none;
  }
  i {
    width: 8px;
    height: 8px;
    display: inline-block;
  }
  @media (max-width: 600px) {
    text,
    .axis-title {
      font-size: 18px;
    }
    .mobile-scroll-note {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }
    .chart-controls {
      padding: 0 18px 16px;
      gap: 10px;
    }
    .plot-region {
      min-height: 280px;
    }
    .plot-scroll {
      min-height: 280px;
    }
    .plot-empty {
      inset: 30px 20px 50px 40px;
    }
    figcaption {
      padding: 16px 18px;
    }
  }
</style>
