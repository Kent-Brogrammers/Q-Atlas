<script lang="ts">
  import type { GraphFixture } from '../data/fixtures.ts';
  import Icon from './Icon.svelte';

  let {
    graph,
    interactive = true,
    compact = false
  }: { graph: GraphFixture; interactive?: boolean; compact?: boolean } = $props();
  const gridId = $props.id();
  let partition = $state<number[] | null>(null);
  let zoom = $state(1);
  let current = $derived(partition ?? graph.assignment);
  let cut = $derived(graph.edges.filter(([i, j]) => current[i] !== current[j]).length);

  $effect(() => {
    graph.id;
    partition = null;
    zoom = 1;
  });

  function toggle(index: number) {
    if (!interactive) return;
    partition = current.map((value, i) => (i === index ? 1 - value : value));
  }

  function keyToggle(event: KeyboardEvent, index: number) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggle(index);
    }
  }
</script>

<div class="graph-view" class:compact>
  {#if !compact}
    <div class="graph-overlay">
      <span class="graph-caption">{partition ? 'Your partition' : 'Reference partition'}</span><span
        class="mono">G = (V, E)</span
      >
    </div>
  {/if}
  <svg
    class="network"
    viewBox="0 0 600 450"
    role={interactive ? 'group' : 'img'}
    aria-label={`${graph.name}, ${graph.nodes.length} vertices and ${graph.edges.length} edges${interactive ? '. Select a node to change its partition.' : ''}`}
  >
    <title>{graph.name} — graph preset</title>
    <defs
      ><pattern id={gridId} width="24" height="24" patternUnits="userSpaceOnUse"
        ><circle cx="1" cy="1" r=".7" fill="var(--border)" /></pattern
      ></defs
    >
    <rect width="600" height="450" fill={`url(#${gridId})`} opacity=".65" />
    <g transform={`translate(${300 * (1 - zoom)} ${225 * (1 - zoom)}) scale(${zoom})`}>
      {#each graph.edges as [i, j]}
        <line
          class="edge"
          class:cut={current[i] !== current[j]}
          x1={graph.nodes[i].x}
          y1={graph.nodes[i].y}
          x2={graph.nodes[j].x}
          y2={graph.nodes[j].y}
        />
      {/each}
      {#snippet nodeContents(node: { x: number; y: number }, i: number)}
        <title>Node {i} · partition {current[i] === 0 ? 'A' : 'B'}</title>
        <circle class="node-hit" cx={node.x} cy={node.y} r="38" />
        <circle class="node-ring" cx={node.x} cy={node.y} r="19" />
        <circle class="node-core" cx={node.x} cy={node.y} r="14" />
        <text x={node.x} y={node.y} dy=".36em" text-anchor="middle">{i}</text>
      {/snippet}
      {#each graph.nodes as node, i}
        {#if interactive}
          <g
            class="node interactive"
            class:partition-b={current[i] === 1}
            role="button"
            tabindex="0"
            aria-label={`Node ${i}, partition ${current[i] === 0 ? 'A' : 'B'}. Move to other partition.`}
            onclick={() => toggle(i)}
            onkeydown={(event) => keyToggle(event, i)}>{@render nodeContents(node, i)}</g
          >
        {:else}
          <g class="node" class:partition-b={current[i] === 1}>{@render nodeContents(node, i)}</g>
        {/if}
      {/each}
    </g>
  </svg>
  {#if !compact}
    <div class="graph-tools">
      <button
        class="icon-button"
        aria-label="Zoom in graph"
        disabled={zoom >= 1.4}
        onclick={() => (zoom = Math.min(1.4, zoom + 0.1))}><Icon name="plus" size={14} /></button
      ><button
        class="icon-button"
        aria-label="Zoom out graph"
        disabled={zoom <= 0.7}
        onclick={() => (zoom = Math.max(0.7, zoom - 0.1))}><Icon name="minus" size={14} /></button
      ><button class="icon-button" aria-label="Fit graph" onclick={() => (zoom = 1)}
        ><Icon name="fit" size={14} /></button
      >
    </div>
    <div class="graph-bottom">
      <div class="graph-legend">
        <span><i class="a"></i>Partition A</span><span><i class="b"></i>Partition B</span>
      </div>
      <p aria-live="polite"><strong>{cut}</strong> / {graph.edges.length} edges cut</p>
    </div>
    {#if interactive}<div class="graph-instructions">
        <span>Select a node to change its partition.</span><button
          onclick={() => (partition = null)}>Reset partition<Icon name="reset" size={12} /></button
        >
      </div>{/if}
  {/if}
</div>

<style>
  .graph-view {
    position: relative;
    background: var(--surface-raised);
    overflow: hidden;
  }
  .network {
    width: 100%;
    display: block;
    max-height: 360px;
    min-height: 260px;
  }
  .graph-overlay {
    position: absolute;
    top: 17px;
    left: 21px;
    right: 21px;
    display: flex;
    justify-content: space-between;
    pointer-events: none;
    z-index: 1;
  }
  .graph-caption {
    font: 12px var(--mono);
    letter-spacing: normal;
    color: var(--muted);
  }
  .graph-overlay .mono {
    font-size: 12px;
    color: var(--muted);
  }
  .edge {
    stroke: var(--border);
    stroke-width: 1.5;
    stroke-dasharray: 5 5;
    transition: stroke 0.2s;
  }
  .edge.cut {
    stroke: var(--blue);
    stroke-dasharray: none;
  }
  .node-hit {
    fill: transparent;
  }
  .node-ring {
    fill: var(--surface);
    stroke: var(--blue);
    stroke-width: 1;
  }
  .node-core {
    fill: var(--bg);
    stroke: var(--blue);
    stroke-width: 1.2;
  }
  .node text {
    fill: var(--blue);
    font: 13px var(--mono);
    pointer-events: none;
  }
  .partition-b .node-ring {
    fill: var(--surface-raised);
    stroke: var(--accent);
  }
  .partition-b .node-core {
    fill: var(--bg);
    stroke: var(--accent);
  }
  .partition-b text {
    fill: var(--accent);
  }
  .interactive {
    cursor: pointer;
    outline: none;
  }
  .interactive:hover .node-ring,
  .interactive:focus-visible .node-ring {
    stroke: var(--blue);
    stroke-width: 2;
  }
  .graph-tools {
    position: absolute;
    right: 17px;
    top: 53px;
    display: grid;
    gap: 5px;
  }
  .graph-tools button {
    width: 27px;
    height: 27px;
    background: var(--surface);
  }
  .graph-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 0 21px 15px;
  }
  .graph-bottom p {
    margin: 0;
    color: var(--muted);
    font: 12px var(--mono);
  }
  .graph-bottom strong {
    color: var(--cyan);
    font-weight: 400;
    font-size: 16px;
  }
  .graph-legend {
    display: flex;
    gap: 14px;
    font-size: 12px;
    color: var(--muted);
  }
  .graph-legend span {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  i {
    width: 6px;
    height: 6px;
    display: inline-block;
    border-radius: 50%;
  }
  i.a {
    background: var(--cyan);
  }
  i.b {
    background: var(--violet);
  }
  .graph-instructions {
    border-top: 1px solid var(--border);
    padding: 12px 21px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--muted);
    font-size: 12px;
  }
  .graph-instructions button {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--blue);
    background: none;
    border: none;
    padding: 0;
    font-size: 12px;
  }
  .compact {
    background: transparent;
    height: 100%;
  }
  .compact .network {
    min-height: 0;
    height: 100%;
    max-height: none;
  }
  .compact .edge.cut {
    stroke: var(--blue);
  }
  @media (prefers-reduced-motion: reduce) {
    .edge {
      transition: none;
    }
  }
</style>
