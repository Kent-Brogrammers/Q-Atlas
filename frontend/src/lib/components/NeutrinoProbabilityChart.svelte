<script lang="ts">
  import type { NeutrinoResponse } from '../../types/index.ts';
  import { curveValues, flavorChannels } from '../neutrinos/live.ts';
  import { formatValue, probabilityPath } from '../neutrinos/presentation.ts';

  let { result = null }: { result?: NeutrinoResponse | null } = $props();
  let extent = $derived(result?.coordinates.at(-1) ?? 0);
  let axis = $derived(
    result?.axis === 'potential'
      ? 'Matter potential (normalized)'
      : 'Propagation distance (normalized)'
  );
</script>

<div class="probability-chart">
  <div class="chart-controls">
    <span class="chart-state">{result ? 'Qiskit Aer · simulated' : 'No experiment run yet'}</span>
  </div>
  <figure>
    <div class="plot-region">
      <!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard users need to scroll the plot.) -->
      <div class="plot-scroll" tabindex="0" role="region" aria-label="Flavor probability plot">
        <svg
          viewBox="0 0 860 330"
          role="img"
          aria-label={`Flavor probabilities versus ${axis.toLowerCase()}`}
        >
          <title>Flavor probabilities versus {axis.toLowerCase()}</title>
          {#each [0, 0.25, 0.5, 0.75, 1] as value}
            <line x1="64" x2="818" y1={272 - value * 230} y2={272 - value * 230} stroke="#e5ebf1" />
            <text x="49" y={276 - value * 230} text-anchor="end">{value}</text>
          {/each}
          <text x="64" y="22" class="axis-title">Flavor probability</text>
          <line x1="64" x2="64" y1="42" y2="272" stroke="#c3cedb" />
          <line x1="64" x2="818" y1="272" y2="272" stroke="#c3cedb" />
          {#each extent > 0 ? [0, 0.25, 0.5, 0.75, 1] : [0] as fraction}
            <text x={64 + fraction * 754} y="295" text-anchor="middle"
              >{formatValue(fraction * extent, 2)}</text
            >
          {/each}
          <text x="818" y="320" text-anchor="end" class="axis-title">{axis}</text>
          {#if result}
            {#each flavorChannels as flavor}
              <path
                d={probabilityPath(
                  result.coordinates,
                  curveValues(result, flavor.key, 'numerical'),
                  extent
                )}
                stroke={flavor.color}
                stroke-width="3"
                fill="none"><title>{flavor.label} · SciPy reference</title></path
              >
              <path
                d={probabilityPath(
                  result.coordinates,
                  curveValues(result, flavor.key, 'ideal'),
                  extent
                )}
                stroke={flavor.color}
                stroke-width="2"
                stroke-dasharray="6 4"
                fill="none"><title>{flavor.label} · ideal Qiskit</title></path
              >
              {#each curveValues(result, flavor.key, 'measured') as probability, i}
                <circle
                  cx={64 + (result.coordinates[i] / (extent || 1)) * 754}
                  cy={272 - probability * 230}
                  r="3"
                  fill={flavor.color}
                  ><title>{flavor.label} · shots {formatValue(probability)}</title></circle
                >
              {/each}
            {/each}
          {/if}
        </svg>
      </div>
      {#if !result}<div class="plot-empty">
          <h3>Run an experiment</h3>
          <p>
            Choose a configuration, then select Run experiment to calculate real simulation results.
          </p>
        </div>{/if}
    </div>
    <figcaption>
      <div class="flavor-legend">
        {#each flavorChannels as flavor}<span
            ><i style:background={flavor.color}></i>{flavor.label}</span
          >{/each}
      </div>
      <p>Solid: SciPy reference · Dashed: ideal Qiskit · Dots: finite-shot measurements</p>
      <p class="mobile-scroll-note">Scroll horizontally to inspect the full plot.</p>
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
    background: #fcfdff;
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
    fill: #596b81;
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
