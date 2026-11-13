<script lang="ts">
  import type { NeutrinoResponse } from '../../types/index.ts';
  import { formatValue as fmt } from '../neutrinos/presentation.ts';
  let {
    result,
    index = $bindable(),
    advanced = false
  }: { result: NeutrinoResponse; index: number; advanced?: boolean } = $props();
  let width = $state(660),
    hover = $state<number | null>(null);
  const channels = [
    { key: 'electron', name: 'Electron flavor', color: 'var(--blue)' },
    { key: 'other', name: 'Other flavor', color: 'var(--lab-teal)' }
  ] as const;
  const methods = ['ideal', 'numerical', 'analytical', 'measured'] as const;
  type Method = (typeof methods)[number];
  let uncertainty = $state(false);
  let visible = $state({ ideal: true, numerical: false, analytical: false, measured: true });
  const labels = {
    ideal: 'Ideal Aer',
    numerical: 'SciPy',
    analytical: 'Analytical',
    measured: 'Shots'
  };
  let extent = $derived(result.coordinates.at(-1) ?? 0);
  let axis = $derived(result.axis === 'distance' ? 'Travel distance' : 'Matter potential');
  let layers = $derived(result.results.at(-1)!.configuration.layers);
  let boundary = $derived(
    result.axis === 'distance' && layers.length === 2 ? layers[0].distance : null
  );
  let marker = $derived(result.axis === 'potential' ? result.resonance_potential : null);
  let end = $derived(Math.max(width, 190) - 18);
  const x = (v: number) => 40 + (v / (extent || 1)) * (end - 40),
    y = (v: number) => 224 - 184 * v;
  function path(method: Method, key: 'electron' | 'other') {
    let connected = false;
    return result.results
      .map((r, i) => {
        const p = r[method]?.[key];
        if (p == null) {
          connected = false;
          return '';
        }
        const cmd = connected ? 'L' : 'M';
        connected = true;
        return cmd + x(result.coordinates[i]) + ',' + y(p);
      })
      .join(' ');
  }
  function target(e: PointerEvent) {
    const box = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const fraction = (e.clientX - box.left - 40) / (end - 40);
    return Math.max(
      0,
      Math.min(
        result.coordinates.length - 1,
        Math.round(fraction * (result.coordinates.length - 1))
      )
    );
  }
  function keypress(e: KeyboardEvent) {
    const n = result.coordinates.length - 1;
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    index =
      e.key === 'Home'
        ? 0
        : e.key === 'End'
          ? n
          : Math.max(0, Math.min(n, index + (e.key === 'ArrowLeft' ? -1 : 1)));
  }
</script>

<div class="legend">
  {#each channels as c}<span><i style:background={c.color}></i>{c.name}</span>{/each}
</div>
<div
  class="plot"
  bind:clientWidth={width}
  role="slider"
  tabindex="0"
  aria-label="Inspect graph point"
  aria-valuemin={0}
  aria-valuemax={result.results.length - 1}
  aria-valuenow={index}
  aria-valuetext={axis + ' ' + fmt(result.coordinates[index])}
  onkeydown={keypress}
  onpointermove={(e) => (hover = target(e))}
  onpointerleave={() => (hover = null)}
  onpointerdown={(e) => (index = target(e))}
>
  <svg
    viewBox={'0 0 ' + Math.max(width, 190) + ' 268'}
    height="268"
    aria-label="Flavor probabilities"
    role="img"
  >
    <title>Probability versus {axis.toLowerCase()}</title>
    {#if boundary !== null}<rect
        x={x(boundary)}
        y="34"
        width={end - x(boundary)}
        height="190"
        fill="var(--blue)"
        opacity=".04"
      /><text x={x(boundary) - 6} y="22" text-anchor="end">Layer 1</text><text
        x={x(boundary) + 6}
        y="22">Layer 2</text
      >{/if}
    {#each [0, 0.25, 0.5, 0.75, 1] as p}<line
        x1="40"
        x2={end}
        y1={y(p)}
        y2={y(p)}
        stroke="var(--lab-border)"
      /><text x="34" y={y(p) + 4} text-anchor="end">{p * 100}%</text>{/each}
    {#each extent ? [0, 0.25, 0.5, 0.75, 1] : [0] as p}<text
        x={x(extent * p)}
        y="246"
        text-anchor="middle">{fmt(extent * p, 2)}</text
      >{/each}
    {#if marker != null && marker <= extent}<text
        x={Math.max(85, Math.min(end - 42, x(marker)))}
        y="22"
        text-anchor="middle"
        class="amber">Resonance</text
      >{/if}
    {#each [boundary, marker] as v}{#if v != null && v <= extent}<line
          x1={x(v)}
          x2={x(v)}
          y1="31"
          y2="224"
          stroke="var(--accent)"
          stroke-dasharray="3 4"
        />{/if}{/each}
    {#each channels as c}
      {#each methods as m}{#if advanced ? visible[m] : m === 'ideal' || m === 'measured'}
          {#if m === 'measured'}{#each result.results as r, i}
              {@const p = r.ideal[c.key]}
              {@const sd = Math.sqrt(Math.max(0, p * (1 - p)) / r.shots)}
              {#if advanced && uncertainty}<line
                  x1={x(result.coordinates[i])}
                  x2={x(result.coordinates[i])}
                  y1={y(Math.min(1, p + sd))}
                  y2={y(Math.max(0, p - sd))}
                  stroke={c.color}
                  stroke-width="2"
                />{/if}
              <circle
                cx={x(result.coordinates[i])}
                cy={y(r.measured[c.key])}
                r="2.4"
                fill={c.color}
              />{/each}
          {:else}<path
              d={path(m, c.key)}
              stroke={c.color}
              stroke-width={m === 'ideal' ? 2 : 3}
              stroke-dasharray={m === 'ideal' ? 'none' : m === 'analytical' ? '2 5' : '8 4'}
              fill="none"
            />{/if}
        {/if}{/each}
    {/each}
    <line
      x1={x(result.coordinates[index])}
      x2={x(result.coordinates[index])}
      y1="34"
      y2="224"
      stroke="var(--subtle)"
      stroke-dasharray="2 5"
    />
    {#each channels as c}{#if !advanced || visible.ideal}<circle
          cx={x(result.coordinates[index])}
          cy={y(result.results[index].ideal[c.key])}
          r="4"
          stroke={c.color}
          fill="var(--surface)"
          stroke-width="2"
        />{/if}{/each}
  </svg>
  {#if hover !== null && result.results[hover]}<div
      class="tip"
      style:left={Math.min(
        Math.max(x(result.coordinates[hover]) - 70, 0),
        Math.max(0, width - 165)
      ) + 'px'}
    >
      {axis}
      {fmt(result.coordinates[hover], 3)}<br />Ideal electron {fmt(
        result.results[hover].ideal.electron * 100,
        2
      )}%<br />Ideal other {fmt(result.results[hover].ideal.other * 100, 2)}%
    </div>{/if}
</div>
<div class="axis">{axis} · normalized</div>
{#if advanced}<div class="overlays">
    {#each methods as m}<label><input type="checkbox" bind:checked={visible[m]} />{labels[m]}</label
      >{/each}
    <label
      ><input type="checkbox" disabled={!visible.measured} bind:checked={uncertainty} />Expected
      shot spread (±1σ)</label
    >
  </div>{:else}<p>
    Lines show ideal probability. Dots show the fraction measured in repeated shots.
  </p>{/if}

<style>
  .legend,
  .overlays {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    font-size: 0.8rem;
  }
  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
  }
  i {
    width: 1.3rem;
    height: 3px;
    border-radius: 3px;
  }
  .plot {
    position: relative;
    cursor: crosshair;
    margin-top: 0.6rem;
  }
  .plot svg {
    width: 100%;
    display: block;
  }
  .plot text {
    font: 11px var(--mono);
    fill: var(--lab-muted);
  }
  .plot .amber {
    fill: var(--accent);
  }
  .axis {
    text-align: center;
    font-size: 0.78rem;
    color: var(--lab-muted);
    margin-top: -0.7rem;
  }
  .tip {
    position: absolute;
    top: 30%;
    pointer-events: none;
    border: 1px solid var(--sidebar);
    background: var(--sidebar);
    color: white;
    padding: 0.55rem;
    border-radius: 2px;
    font-size: 0.75rem;
  }
  .overlays,
  p {
    margin: 0.9rem 0 0;
    color: var(--lab-muted);
    font-size: 0.77rem;
  }
  .overlays input {
    margin-right: 0.35rem;
    accent-color: var(--lab-teal);
  }
</style>
