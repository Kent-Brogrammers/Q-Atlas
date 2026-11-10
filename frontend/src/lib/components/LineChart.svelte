<script lang="ts">
  let { values, optimum }: { values: number[]; optimum: number } = $props();
  let max = $derived(Math.ceil(Math.max(...values)));
  let min = $derived(optimum);
  let y = $derived((value: number) => 25 + ((max - value) / Math.max(1, max - min)) * 160);
  let path = $derived(
    values
      .map(
        (value, i) => `${i === 0 ? 'M' : 'L'}${50 + (i / (values.length - 1)) * 480},${y(value)}`
      )
      .join(' ')
  );
</script>

<figure class="line-chart">
  <svg
    viewBox="0 0 565 230"
    role="img"
    aria-label="Example QAOA objective display. Points are illustrative; no optimizer was run."
  >
    <title>Example objective trace, not measured data</title>
    {#each [0, 1, 2, 3, 4] as tick}
      {@const value = max - (tick / 4) * (max - min)}
      <line x1="50" x2="530" y1={y(value)} y2={y(value)} stroke="#e5edf5" stroke-width=".7" />
      <text x="36" y={y(value) + 3} text-anchor="end"
        >{Number.isInteger(value) ? value : value.toFixed(1)}</text
      >
    {/each}
    <line
      x1="50"
      x2="530"
      y1={y(optimum)}
      y2={y(optimum)}
      stroke="#72b9b4"
      stroke-width="1"
      stroke-dasharray="4 5"
    />
    <path d={path} fill="none" stroke="#55a0ea" stroke-width="2" stroke-linejoin="round" />
    {#each values as value, i}
      <circle
        cx={50 + (i / (values.length - 1)) * 480}
        cy={y(value)}
        r="3"
        fill="#ffffff"
        stroke="#7bb4ed"
        stroke-width="1.5"><title>Example point {i + 1}: {value.toFixed(2)}</title></circle
      >
    {/each}
    {#each [1, 4, 8, 12, 16] as tick}
      <text x={50 + ((tick - 1) / 15) * 480} y="207" text-anchor="middle">{tick}</text>
    {/each}
    <text x="530" y="226" text-anchor="end">example point</text>
  </svg>
  <figcaption>
    <span><i></i>Example QAOA cost</span><span><i class="reference"></i>Exact reference</span><span
      class="direction">Lower is better ↓</span
    >
  </figcaption>
</figure>

<style>
  figure {
    margin: 0;
    padding: 0 16px 20px 8px;
  }
  svg {
    width: 100%;
    display: block;
  }
  text {
    fill: #6f8198;
    font: 12px var(--mono);
  }
  figcaption {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 10px 8px 0 40px;
    color: #647387;
    font-size: 12px;
    flex-wrap: wrap;
  }
  figcaption > span {
    display: inline-flex;
    align-items: center;
    gap: 7px;
  }
  i {
    display: inline-block;
    width: 13px;
    height: 2px;
    background: #55a0ea;
  }
  i.reference {
    background: #72b9b4;
  }
  .direction {
    margin-left: auto;
    color: #899ab0;
  }
</style>
