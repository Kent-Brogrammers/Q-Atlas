<script lang="ts">
  import { graphs } from '../data/fixtures.ts';
  import Icon from './Icon.svelte';
</script>

<div class="library-chart">
  <svg
    viewBox="0 0 180 180"
    role="img"
    aria-label="Three example problem fixtures: triangular prism, cube graph, and four-node cycle. This is a library inventory, not a benchmark result."
  >
    <title>Example problem library</title>
    <circle cx="90" cy="90" r="65" fill="none" stroke="#f0f4f9" stroke-width="12" />
    {#each ['#43a5ef', '#8bc9dd', '#b0a1d1'] as color, i}<circle
        cx="90"
        cy="90"
        r="65"
        fill="none"
        stroke={color}
        stroke-width="12"
        stroke-linecap="round"
        stroke-dasharray="119 409"
        stroke-dashoffset={-i * 136.1}
        transform="rotate(-85 90 90)"
      />{/each}
    <text x="90" y="89" text-anchor="middle" class="chart-number">03</text><text
      x="90"
      y="110"
      text-anchor="middle"
      class="chart-label">problem fixtures</text
    >
  </svg>
  <div class="library-legend">
    {#each graphs as graph, i}<div>
        <i class="legend-dot color-{i}"></i><span>{graph.name}</span><strong
          >{graph.nodes.length}<small>vars</small></strong
        >
      </div>{/each}
  </div>
  <div class="library-foot">
    <span><Icon name="graph" size={13} />Curated example library</span><span>Local data</span>
  </div>
</div>

<style>
  .library-chart {
    padding: 0 23px;
  }
  svg {
    display: block;
    width: 180px;
    max-width: 85%;
    margin: 0 auto 16px;
  }
  .chart-number {
    fill: #273951;
    font:
      500 31px 'IBM Plex Sans',
      sans-serif;
    letter-spacing: -1px;
  }
  .chart-label {
    fill: #728298;
    font:
      10px 'IBM Plex Sans',
      sans-serif;
  }
  .library-legend {
    display: grid;
    gap: 13px;
    padding-bottom: 21px;
  }
  .library-legend > div {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: #667387;
  }
  .legend-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }
  .color-0 {
    background: #43a5ef;
  }
  .color-1 {
    background: #8bc9dd;
  }
  .color-2 {
    background: #b0a1d1;
  }
  strong {
    font:
      500 12px 'IBM Plex Sans',
      sans-serif;
    color: #344863;
    margin-left: auto;
  }
  small {
    font-size: 9px;
    color: #6a737e;
    margin-left: 4px;
    font-weight: 400;
  }
  .library-foot {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    border-top: 1px solid #edf1f6;
    margin: 0 -23px;
    padding: 15px 22px;
    color: #8897aa;
    font-size: 9px;
  }
  .library-foot > span:first-child {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
</style>
