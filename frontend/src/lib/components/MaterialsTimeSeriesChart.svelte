<script lang="ts">
  import type { MaterialsResult } from '../../types/index.ts';

  type TimePoint = NonNullable<MaterialsResult['metrics']['time_series']>[number];
  type Observable = 'energy' | 'magnetization_z';

  let {
    points,
    observable,
    unit
  }: {
    points: TimePoint[];
    observable: Observable;
    unit: string;
  } = $props();

  const width = 700;
  const height = 300;
  const left = 62;
  const right = 18;
  const top = 18;
  const bottom = 48;

  let chart = $derived.by(() => {
    const samples = points.map((point) => ({
      time: point.time,
      exact: point.exact[observable],
      ideal: point.ideal[observable],
      measured: point.measured[observable]
    }));
    const values = samples.flatMap((point) => [point.exact, point.ideal, point.measured]);
    const rawMin = Math.min(...values);
    const rawMax = Math.max(...values);
    const padding = Math.max((rawMax - rawMin) * 0.12, Math.abs(rawMin) * 0.04, 0.04);
    const minValue = rawMin - padding;
    const maxValue = rawMax + padding;
    const minTime = samples[0]?.time ?? 0;
    const maxTime = samples.at(-1)?.time ?? 0;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const x = (time: number) => left + ((time - minTime) / (maxTime - minTime || 1)) * plotWidth;
    const y = (value: number) => top + ((maxValue - value) / (maxValue - minValue)) * plotHeight;
    const seriesDefinitions = [
      { key: 'exact', label: 'Exact reference', color: '#2674c8' },
      { key: 'ideal', label: 'Ideal Trotter circuit', color: '#8066b2' },
      { key: 'measured', label: 'Shot-based circuit', color: '#16877f' }
    ] as const;
    const lines = seriesDefinitions.map((series) => {
      const coordinates = samples.map((point) => ({
        x: x(point.time),
        y: y(point[series.key]),
        time: point.time,
        value: point[series.key]
      }));
      return {
        ...series,
        coordinates,
        path: coordinates
          .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`)
          .join(' ')
      };
    });

    return {
      lines,
      ticks: Array.from({ length: 5 }, (_, index) => {
        const value = minValue + ((maxValue - minValue) * index) / 4;
        return { value, y: y(value) };
      }),
      minTime,
      maxTime,
      x,
      plotBottom: height - bottom,
      plotRight: width - right
    };
  });
</script>

<section class="chart-section" aria-labelledby="materials-chart-title">
  <h3 id="materials-chart-title">
    Time evolution · {observable === 'energy' ? 'energy' : 'Z magnetization'}
  </h3>
  <figure>
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Exact, ideal circuit, and shot-based ${observable} over simulation time in ${unit}`}
    >
      {#each chart.ticks as tick}
        <line x1={left} x2={chart.plotRight} y1={tick.y} y2={tick.y} stroke="#e6ebf1" />
        <text x={left - 8} y={tick.y + 4} text-anchor="end">{tick.value.toFixed(3)}</text>
      {/each}
      <line
        x1={left}
        x2={chart.plotRight}
        y1={chart.plotBottom}
        y2={chart.plotBottom}
        stroke="#aab7c6"
      />
      {#each chart.lines as line}
        <path d={line.path} fill="none" stroke={line.color} stroke-width="2" />
        {#each line.coordinates as point}
          <circle cx={point.x} cy={point.y} r="3.5" fill={line.color}>
            <title>{line.label}: t={point.time.toFixed(3)}, {point.value.toFixed(5)}</title>
          </circle>
        {/each}
      {/each}
      <text x={left} y={height - 12} text-anchor="start">{chart.minTime.toFixed(2)}</text>
      <text x={chart.plotRight} y={height - 12} text-anchor="end">{chart.maxTime.toFixed(2)}</text>
      <text x={(left + chart.plotRight) / 2} y={height - 12} text-anchor="middle">
        Simulation time (dimensionless)
      </text>
    </svg>
    <figcaption>
      {#each chart.lines as line}
        <span><i style={`--series-color:${line.color}`}></i>{line.label}</span>
      {/each}
      <span class="unit-label">{unit}</span>
    </figcaption>
  </figure>
</section>

<style>
  .chart-section {
    margin: 0 24px 18px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
  }
  h3 {
    margin: 0 0 8px;
    color: #45566d;
    font-size: 12px;
    font-weight: 500;
  }
  figure {
    margin: 0;
  }
  svg {
    display: block;
    width: 100%;
    overflow: visible;
  }
  text {
    fill: #6f8198;
    font: 10px var(--mono);
  }
  figcaption {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: center;
    padding: 8px 0 0 18px;
    color: var(--muted);
    font-size: 11px;
  }
  figcaption > span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  i {
    width: 13px;
    height: 2px;
    background: var(--series-color);
  }
  .unit-label {
    margin-left: auto;
  }
  @media (max-width: 650px) {
    .chart-section {
      margin-inline: 16px;
    }
    figcaption {
      padding-left: 0;
    }
  }
</style>
