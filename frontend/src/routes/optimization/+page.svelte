<script lang="ts">
  import { onMount } from 'svelte';
  import { largerWorkload } from '#lib/presentation/workloads.ts';
  import { graphs } from '#lib/data/fixtures.ts';
  import Panel from '#lib/components/Panel.svelte';
  import GraphView from '#lib/components/GraphView.svelte';
  import OptimizationWorkspace from '#lib/components/OptimizationWorkspace.svelte';
  import { cycleProblem } from '#lib/studies/model.ts';
  import type { OptimizationRequest } from '../../types/index.ts';
  let selected = $state('prism');
  onMount(() => {
    if (new URL(window.location.href).searchParams.get('example') === 'large') selected = 'large';
  });
  let size = $state(6);
  let custom = $state(JSON.stringify(cycleProblem(4), null, 2));
  let graph = $derived(graphs.find((item) => item.id === selected));
  let input = $derived.by(() => {
    if (selected === 'large') return { problem: largerWorkload(), error: '' };
    if (selected === 'generated') return { problem: cycleProblem(size), error: '' };
    if (selected !== 'custom')
      return { problem: { kind: 'qubo' as const, qubo: graph!.qubo }, error: '' };
    try {
      const parsed = JSON.parse(custom);
      if (!parsed || !['graph', 'qubo'].includes(parsed.kind))
        throw new Error('Use kind "graph" or "qubo".');
      return { problem: parsed as OptimizationRequest['problem'], error: '' };
    } catch (cause) {
      return {
        problem: undefined,
        error: cause instanceof Error ? cause.message : 'Invalid JSON.'
      };
    }
  });
  let problem = $derived(input.problem);
</script>

<svelte:head><title>Max-Cut Optimization · Q-Atlas</title></svelte:head>
<header class="page-heading">
  <div>
    <h1>Max-Cut Optimization</h1>
    <p>Compare exact classical enumeration with QAOA on the same graph.</p>
  </div>
</header>
<Panel title="Choose a graph" subtitle="Mathematical inputs · results appear only after execution">
  <div class="graph-controls">
    <label
      >Graph<select bind:value={selected}
        >{#each graphs as item}<option value={item.id}
            >{item.name} · {item.nodes.length} vertices</option
          >{/each}<option value="large">Larger workload · 16 choices, 65,536 assignments</option
        ><option value="generated">Cycle graph · choose size</option><option value="custom"
          >Custom weighted graph / QUBO JSON</option
        ></select
      ></label
    >
    {#if selected === 'large'}<p>
        <strong>Real larger benchmark:</strong> 16 binary choices, 120 weighted edges, 65,536 possible
        assignments. Exact solving and quantum simulation can take seconds or reach their timeout. This
        preset is for local execution; physical runs support up to eight choices.
      </p>{/if}
    {#if selected === 'generated'}<label
        >Vertices<select bind:value={size}
          >{#each Array.from({ length: 14 }, (_, i) => i + 3) as n}<option value={n}>{n}</option
            >{/each}</select
        ></label
      >{/if}
    {#if selected === 'custom'}
      <label for="custom-problem">Graph or QUBO JSON</label>
      <textarea
        id="custom-problem"
        rows="12"
        maxlength="20000"
        spellcheck="false"
        bind:value={custom}
      ></textarea>
      <p>
        Graph: kind, num_vertices, edges (i, j, coefficient). QUBO: kind and qubo (num_variables,
        constant, linear, quadratic, sense). The backend validates all indices, coefficients and
        resource limits.
      </p>
      {#if input.error}<p role="alert">{input.error}</p>{/if}
    {/if}
    <p>
      Max-Cut maximizes crossing edges. The canonical QUBO minimizes the negative cut weight. Both
      solvers receive the identical QUBO.
    </p>
  </div>
  {#if graph}<GraphView {graph} />{/if}
  <details>
    <summary>Inspect mathematical input</summary>
    <pre>{JSON.stringify(problem, null, 2)}</pre>
  </details>
</Panel>
<OptimizationWorkspace {problem} />
<Panel title="How this comparison works"
  ><div class="explanation">
    <p>
      QAOA alternates a cost circuit and an X mixer. A classical COBYLA optimizer trains 2p angles
      using ideal statevector expectations, then Aer samples the final circuit. The exact baseline
      enumerates all assignments. The sampled gap reports solution quality alongside runtime.
    </p>
    <p>
      The simulator evaluates exponentially many amplitudes and objective values on a CPU. These
      measurements establish implementation behavior, not hardware speedup. For larger benchmark
      studies, include the classical multistart heuristic using the repository's stress benchmark
      CLI.
    </p>
  </div></Panel
>

<style>
  .graph-controls,
  .explanation {
    padding: 0 22px 22px;
  }
  label {
    display: grid;
    gap: 8px;
    max-width: 420px;
    margin-bottom: 15px;
    font-size: 13px;
  }
  select {
    padding: 10px;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--border);
  }
  textarea {
    width: 100%;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 12px;
    font: 12px var(--mono);
  }
  p {
    font-size: 13px;
    line-height: 1.7;
    color: var(--muted);
  }
  details {
    padding: 20px;
  }
  pre {
    max-height: 260px;
    overflow: auto;
    font-size: 12px;
  }
</style>
