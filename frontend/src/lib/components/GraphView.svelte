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
      <span class="graph-caption">{partition ? 'YOUR PARTITION' : 'REFERENCE PARTITION'}</span><span
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
    <title>{graph.name} — example graph</title>
    <defs
      ><pattern id={gridId} width="24" height="24" patternUnits="userSpaceOnUse"
        ><circle cx="1" cy="1" r=".7" fill="#c7d8e9" /></pattern
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
        <span>Click a node to explore the cut.</span><button onclick={() => (partition = null)}
          >Reset partition<Icon name="reset" size={12} /></button
        >
      </div>{/if}
  {/if}
</div>

<style>
  .graph-view {
    position: relative;
    background: #f7faff;
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
    font: 8px var(--mono);
    letter-spacing: 0.08em;
    color: #647385;
  }
  .graph-overlay .mono {
    font-size: 9px;
    color: #9cacc0;
  }
  .edge {
    stroke: #d0dce9;
    stroke-width: 1.5;
    stroke-dasharray: 5 5;
    transition: stroke 0.2s;
  }
  .edge.cut {
    stroke: #6ba8df;
    stroke-dasharray: none;
  }
  .node-hit {
    fill: transparent;
  }
  .node-ring {
    fill: #f1f9ff;
    stroke: #a9cfe9;
    stroke-width: 1;
  }
  .node-core {
    fill: #e5f3ff;
    stroke: #49a0d1;
    stroke-width: 1.2;
  }
  .node text {
    fill: #2a729c;
    font: 13px var(--mono);
    pointer-events: none;
  }
  .partition-b .node-ring {
    fill: #faf7ff;
    stroke: #d9c9ea;
  }
  .partition-b .node-core {
    fill: #f0eaf8;
    stroke: #a58ac7;
  }
  .partition-b text {
    fill: #795a9e;
  }
  .interactive {
    cursor: pointer;
    outline: none;
  }
  .interactive:hover .node-ring,
  .interactive:focus-visible .node-ring {
    stroke: #0f62fe;
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
    background: #ffffff;
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
    color: #667385;
    font: 10px var(--mono);
  }
  .graph-bottom strong {
    color: var(--cyan);
    font-weight: 400;
    font-size: 16px;
  }
  .graph-legend {
    display: flex;
    gap: 14px;
    font-size: 9px;
    color: #677382;
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
    border-top: 1px solid #e4edf6;
    padding: 12px 21px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #8a9bb0;
    font-size: 9px;
  }
  .graph-instructions button {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #5583b5;
    background: none;
    border: none;
    padding: 0;
    font-size: 9px;
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
    stroke: #a4c7e7;
  }
  @media (prefers-reduced-motion: reduce) {
    .edge {
      transition: none;
    }
  }
</style>
