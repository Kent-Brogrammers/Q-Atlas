<script lang="ts">
  let {
    rows,
    metrics,
    label,
    xLabel = 'Selected parameter value'
  }: {
    rows: {
      value: number;
      metrics: Record<string, { median: number | null; min: number | null; max: number | null }>;
    }[];
    metrics: string[];
    label: string;
    xLabel?: string;
  } = $props();
  const colors = ['#0f62fe', '#8a3ffc', '#00869b'];
  let values = $derived(
    rows
      .flatMap((row) => metrics.flatMap((key) => [row.metrics[key]?.min, row.metrics[key]?.max]))
      .filter((x): x is number => typeof x === 'number' && Number.isFinite(x))
  );
  let low = $derived(Math.min(0, ...values));
  let high = $derived(Math.max(0.001, ...values));
  let x = $derived(
    (value: number) =>
      70 +
      (510 * (value - Math.min(...rows.map((r) => r.value)))) /
        Math.max(1, Math.max(...rows.map((r) => r.value)) - Math.min(...rows.map((r) => r.value)))
  );
  let y = $derived((value: number) => 205 - (170 * (value - low)) / Math.max(0.001, high - low));
</script>

<figure>
  <svg viewBox="0 0 640 260" role="img" aria-label={label}>
    <title>{label}: medians with observed minimum and maximum</title>
    {#each [0, 0.5, 1] as fraction}
      {@const value = low + (high - low) * fraction}
      <line x1="70" x2="585" y1={y(value)} y2={y(value)} stroke="var(--border)" />
      <text x="60" y={y(value) + 4} text-anchor="end">{value.toPrecision(3)}</text>
    {/each}
    {#each metrics as metric, index}
      {#each rows as row}
        {@const m = row.metrics[metric]}
        {#if m?.median != null}
          {#if m.min != null && m.max != null}<line
              x1={x(row.value)}
              x2={x(row.value)}
              y1={y(m.min)}
              y2={y(m.max)}
              stroke={colors[index % 3]}
              stroke-width="3"
            />{/if}
          <circle cx={x(row.value)} cy={y(m.median)} r="4" fill={colors[index % 3]}
            ><title>{metric}, {row.value}: median {m.median}, range {m.min}–{m.max}</title></circle
          >
        {/if}
      {/each}
    {/each}
    {#each rows as row}<text x={x(row.value)} y="230" text-anchor="middle">{row.value}</text>{/each}
    <text x="320" y="254" text-anchor="middle">{xLabel}</text>
  </svg>
  <figcaption>
    {#each metrics as metric, index}<span style:color={colors[index % 3]}>{metric}</span>{/each}
  </figcaption>
</figure>

<style>
  figure {
    margin: 12px 0;
  }
  svg {
    display: block;
    width: 100%;
    max-width: 800px;
  }
  text {
    fill: var(--muted);
    font: 11px var(--mono);
  }
  figcaption {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 12px;
  }
</style>
