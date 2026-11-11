<script lang="ts">
  import type { CurvePoint } from './live.ts';
  let {
    points,
    measurementLabel = 'Measured Aer shots'
  }: { points: CurvePoint[]; measurementLabel?: string } = $props();
  let hasRanges = $derived(points.some((point) => point.observedRange !== undefined));
  let hasIntervals = $derived(points.some((point) => point.confidenceInterval !== undefined));
  let last = $derived(Math.max(1, ...points.map((point) => point.iteration)));
  const y = (probability: number) => 210 - probability * 180;
  let x = $derived((iteration: number) => 55 + (iteration / last) * 490);
  function path(key: 'measured' | 'theoretical') {
    let penDown = false;
    return points
      .map((point) => {
        const value = point[key];
        if (value === null) {
          penDown = false;
          return '';
        }
        const command = `${penDown ? 'L' : 'M'}${x(point.iteration)},${y(value)}`;
        penDown = true;
        return command;
      })
      .join(' ');
  }
</script>

<figure>
  {#if points.length}
    <svg
      viewBox="0 0 580 265"
      role="img"
      aria-label="Measured and theoretical Grover success probability versus iterations"
    >
      <title>Grover success probability at integer iterations</title>
      {#each [0, 0.25, 0.5, 0.75, 1] as tick}
        <line x1="55" x2="545" y1={y(tick)} y2={y(tick)} stroke="var(--border)" />
        <text x="44" y={y(tick) + 4} text-anchor="end">{tick * 100}%</text>
      {/each}
      {#each points as point}<text x={x(point.iteration)} y="232" text-anchor="middle"
          >{point.iteration}</text
        >{/each}
      <path
        d={path('theoretical')}
        fill="none"
        stroke="#7864b4"
        stroke-width="2"
        stroke-dasharray="6 4"
      />
      <path d={path('measured')} fill="none" stroke="#0f62fe" stroke-width="2" />
      {#each points as point}
        {#if point.confidenceInterval}
          <g stroke="var(--blue)" stroke-width="2" stroke-dasharray="3 2">
            <title
              >95% Wilson sampling interval at iteration {point.iteration}:
              {(point.confidenceInterval[0] * 100).toFixed(2)}% to
              {(point.confidenceInterval[1] * 100).toFixed(2)}%</title
            >
            <line
              x1={x(point.iteration)}
              x2={x(point.iteration)}
              y1={y(point.confidenceInterval[0])}
              y2={y(point.confidenceInterval[1])}
            />
            {#each point.confidenceInterval as bound}
              <line
                x1={x(point.iteration) - 5}
                x2={x(point.iteration) + 5}
                y1={y(bound)}
                y2={y(bound)}
              />
            {/each}
          </g>
        {/if}
        {#if point.observedRange}
          <g stroke="#0f62fe" stroke-width="2">
            <title
              >Observed trial range: {(point.observedRange[0] * 100).toFixed(2)}% to {(
                point.observedRange[1] * 100
              ).toFixed(2)}%; not a confidence interval</title
            >
            <line
              x1={x(point.iteration)}
              x2={x(point.iteration)}
              y1={y(point.observedRange[0])}
              y2={y(point.observedRange[1])}
            />
            {#each point.observedRange as bound}
              <line
                x1={x(point.iteration) - 6}
                x2={x(point.iteration) + 6}
                y1={y(bound)}
                y2={y(bound)}
              />
            {/each}
          </g>
        {/if}
        {#if point.theoretical !== null}<circle
            cx={x(point.iteration)}
            cy={y(point.theoretical)}
            r="5"
            fill="white"
            stroke="#7864b4"
            stroke-width="2"
            ><title
              >Iteration {point.iteration}: theory {(point.theoretical * 100).toFixed(2)}%</title
            ></circle
          >{/if}
        {#if point.measured !== null}<circle
            cx={x(point.iteration)}
            cy={y(point.measured)}
            r="3"
            fill="#0f62fe"
            ><title
              >Iteration {point.iteration}: measured {(point.measured * 100).toFixed(2)}%</title
            ></circle
          >{/if}
      {/each}
      <text x="300" y="258" text-anchor="middle">Grover iterations / oracle calls per shot</text>
    </svg>
    <figcaption>
      <span class="measured">● {measurementLabel}</span><span class="theory">○ Ideal theory</span>
    </figcaption>
    <p class="hint">
      {hasRanges
        ? 'Whisker: observed min/max across trials, not a confidence interval.'
        : 'Lines join integer-iteration samples.'}
      {#if hasIntervals}Dashed whiskers: pointwise 95% Wilson sampling intervals, not a simultaneous
        confidence band.{/if} The table below provides every value.
    </p>
  {:else}
    <div class="empty">
      <strong>No measurements yet</strong>
      <p>Run a comparison or measure a curve. Results come from your local backend.</p>
    </div>
  {/if}
</figure>

<style>
  figure {
    margin: 0;
    padding: 0 24px 20px;
  }
  svg {
    display: block;
    width: 100%;
  }
  text {
    fill: var(--muted);
    font: 11px var(--mono);
  }
  figcaption {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    font-size: 13px;
  }
  .measured {
    color: #0f62fe;
  }
  .theory {
    color: #7864b4;
  }
  .hint,
  .empty p {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
  }
  .empty {
    min-height: 245px;
    display: grid;
    align-content: center;
    text-align: center;
  }
  .empty strong {
    font-weight: 500;
  }
</style>
