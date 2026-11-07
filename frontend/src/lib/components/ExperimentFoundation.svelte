<script lang="ts">
  import { experiments } from '../data/experiments.ts';
  import type { Experiment } from '../types/contracts.ts';
  import Icon from './Icon.svelte';
  import Panel from './Panel.svelte';
  import ExampleNotice from './ExampleNotice.svelte';
  import CircuitDiagram from './CircuitDiagram.svelte';

  let { experiment }: { experiment: Exclude<Experiment, 'optimization'> } = $props();
  let info = $derived(experiments.find((item) => item.id === experiment)!);
  const exampleSource =
    '@qatlas.objective(num_bits=3)\ndef objective(x):\n    return 3 - x[0] + 2*x[1] - 2*x[0]*x[1]\n';
  const exampleQubo = {
    num_variables: 3,
    constant: 3,
    linear: [-1, 2, 0],
    quadratic: [{ i: 0, j: 1, coefficient: -2 }],
    sense: 'minimize'
  };
  let source = $state(exampleSource);
  let preview = $state(false);
  let spins = $state(4);
  let coupling = $state(1);
  let field = $state(0.5);
  let space = $state(16);
  let marked = $state(5);
  let status = $state('');

  const comparisons: Record<string, { title: string; description: string }[]> = {
    compiler: [
      {
        title: 'Source validation (planned)',
        description: 'Allowlisted AST analysis with diagnostics. User source is never executed.'
      },
      {
        title: 'QUBO normalization (planned)',
        description: 'Canonical minimization, normalized terms, and explicit variable order.'
      },
      {
        title: 'QAOA integration (planned)',
        description: 'The same optimization engine serves the compiler and Max-Cut experiments.'
      }
    ],
    materials: [
      {
        title: 'Spin Hamiltonian (planned)',
        description: 'Two to four spins, with explicit model assumptions and parameters.'
      },
      {
        title: 'Exact diagonalization (planned)',
        description: 'A defined observable checked against exact diagonalization.'
      },
      {
        title: 'Observable comparison (planned)',
        description: 'Report absolute error, units, backend, and timing scope.'
      }
    ],
    search: [
      {
        title: 'Oracle construction (planned)',
        description: 'Marked states and oracle-construction assumptions remain visible.'
      },
      {
        title: 'Probability and query counts (planned)',
        description: 'Compare success probabilities and query complexity separately from runtime.'
      },
      {
        title: 'Classical baseline (planned)',
        description: 'Use the same search problem and account for predicate implementation.'
      }
    ]
  };
</script>

<svelte:head><title>{info.title} · Q-Atlas</title></svelte:head>
<header class="page-heading">
  <div>
    <p class="eyebrow">{info.method}</p>
    <h1>{info.title}</h1>
    <p>{info.description}</p>
  </div>
</header>
<ExampleNotice />

{#if experiment === 'compiler'}
  <div class="foundation-grid compiler-grid">
    <Panel
      title="Python source"
      subtitle="Source stays in your browser; compiler integration is pending."
    >
      {#snippet toolbar()}<span class="file-label">objective.py</span>{/snippet}
      <div class="source-editor">
        <div aria-hidden="true" class="line-numbers">
          {#each source.split('\n') as _, i}<span>{i + 1}</span>{/each}
        </div>
        <textarea
          id="objective-source"
          name="source"
          aria-label="Python objective source"
          bind:value={source}
          oninput={() => {
            preview = false;
            status = '';
          }}
          spellcheck="false"
        ></textarea>
      </div>
      <div class="editor-actions">
        <span>No source execution or analysis</span><button
          class="button small"
          onclick={() => {
            source = exampleSource;
            preview = true;
            status = 'Loaded the bundled example output. No compiler was run.';
          }}>Load bundled example<Icon name="arrow" size={15} /></button
        >
      </div>
      <p class="editor-status" role="status">
        {status || 'Source edits are not analyzed. Load the bundled example to inspect its QUBO.'}
      </p>
    </Panel>
    <Panel title="QUBO extraction">
      {#if preview}<div class="output-label">Example QUBO · not compiler output</div>
        <pre class="code-block">{JSON.stringify(exampleQubo, null, 2)}</pre>{:else}<div
          class="empty-state"
        >
          <Icon name="code" size={32} />
          <h3>No QUBO extracted</h3>
          <p>
            Load the bundled example to inspect its hand-authored QUBO. Editing source does not
            trigger extraction.
          </p>
        </div>{/if}
    </Panel>
  </div>
  <Panel
    title="QAOA circuit schematic"
    subtitle="A conceptual QAOA layer schematic. Circuit generation is not connected."
    ><CircuitDiagram /></Panel
  >
{:else if experiment === 'materials'}
  <div class="foundation-grid">
    <Panel title="Model setup" subtitle="Illustrative controls for a small Ising chain.">
      <div class="foundation-controls">
        <label for="spins">Spin count<output>{spins}</output></label><input
          id="spins"
          type="range"
          min="2"
          max="4"
          step="1"
          bind:value={spins}
        /><label for="coupling">Coupling J (model units)</label><input
          id="coupling"
          type="number"
          min="-5"
          max="5"
          step="0.1"
          bind:value={coupling}
        /><label for="field">Field h (model units)</label><input
          id="field"
          type="number"
          min="-5"
          max="5"
          step="0.1"
          bind:value={field}
        />
        <p>Parameters describe a model preview. No Hamiltonian or observable is computed here.</p>
      </div>
    </Panel>
    <Panel title="Spin-chain schematic">
      <div class="spin-illustration">
        <svg
          viewBox="0 0 600 220"
          role="img"
          aria-label={`Conceptual chain of ${spins} spins. No simulation output.`}
          ><title>Spin-chain schematic</title
          >{#each Array.from({ length: spins }) as _, i}{@const x =
              100 + (i * 400) / (spins - 1)}{#if i < spins - 1}<line
                x1={x + 33}
                x2={100 + ((i + 1) * 400) / (spins - 1) - 33}
                y1="100"
                y2="100"
                stroke="#cedceb"
              />{/if}<circle cx={x} cy="100" r="31" fill="#f5f0fb" stroke="#c6b4df" /><path
              d={`M${x} ${i % 2 ? 115 : 85}v${i % 2 ? -30 : 30}m-7 ${i % 2 ? 23 : -23} 7 ${i % 2 ? 7 : -7} 7 ${i % 2 ? -7 : 7}`}
              fill="none"
              stroke="#9d81c5"
              stroke-width="2"
            /><text {x} y="157" text-anchor="middle">spin {i}</text>{/each}</svg
        >
        <p class="mono">
          J = {coupling ?? '—'} <span>/</span> h = {field ?? '—'} <span>/</span>
          {spins} spins
        </p>
        <span>Conceptual diagram · no physical result</span>
      </div>
    </Panel>
  </div>
{:else}
  <div class="foundation-grid">
    <Panel title="Search settings" subtitle="Select a marked state to inspect the UI.">
      <div class="foundation-controls">
        <label for="space">Number of states</label><select
          id="space"
          bind:value={space}
          onchange={() => (marked = 0)}
          ><option value={4}>4 states · 2 qubits</option><option value={8}
            >8 states · 3 qubits</option
          ><option value={16}>16 states · 4 qubits</option></select
        >
        <div class="marked-label">
          <span class="eyebrow">Marked state</span><strong
            >|{marked.toString(2).padStart(Math.log2(space), '0')}⟩</strong
          >
        </div>
        <p>
          States below are illustrative oracle labels. This view does not construct an oracle or
          execute Grover's algorithm.
        </p>
      </div>
    </Panel>
    <Panel title="Search states" subtitle="Click any state to mark it."
      ><div class="state-grid">
        {#each Array.from({ length: space }) as _, i}<button
            class:marked={marked === i}
            aria-pressed={marked === i}
            aria-label={`Mark state ${i}`}
            onclick={() => (marked = i)}
            ><span>|{i.toString(2).padStart(Math.log2(space), '0')}⟩</span><i
              >{marked === i ? 'Marked' : 'State'}</i
            ></button
          >{/each}
      </div>
      <p class="state-note">
        State-label illustration. API bitstrings use x[0] first; Qiskit counts require conversion.
      </p></Panel
    >
  </div>
{/if}

<div class="integration-row">
  <Panel title="Pending backend integration"
    ><div class="comparison-plan">
      {#each comparisons[experiment] as item, i}<div>
          <span class="mono">0{i + 1}</span>
          <p><strong>{item.title}</strong>{item.description}</p>
        </div>{/each}
    </div></Panel
  >
  <section class="next-workspace">
    <h2>Max-Cut optimization</h2>
    <p>Inspect graph partitions, canonical QUBOs, and optional example result charts.</p>
    <a class="text-link" href="/optimization/">Open optimization<Icon name="arrow" size={16} /></a>
  </section>
</div>

<style>
  .foundation-grid {
    display: grid;
    grid-template-columns: minmax(230px, 0.7fr) minmax(0, 1.5fr);
    gap: 20px;
    margin: 24px 0;
  }
  .compiler-grid {
    grid-template-columns: 1.3fr 1fr;
  }
  .file-label {
    color: #637387;
    font: 12px var(--mono);
  }
  input[type='number'] {
    font-family: var(--mono);
  }
  .source-editor {
    display: flex;
    background: #f8fafd;
    border-top: 1px solid var(--border);
    min-height: 245px;
    padding: 23px 0;
  }
  .line-numbers {
    display: flex;
    flex-direction: column;
    width: 43px;
    padding-right: 10px;
    text-align: right;
    color: #9baabd;
    font: 12px/2.1 var(--mono);
    user-select: none;
  }
  textarea {
    width: calc(100% - 43px);
    border: 0;
    resize: vertical;
    min-height: 200px;
    background: transparent;
    color: #496b9b;
    padding: 0 16px 0 5px;
    font: 12px/2.1 var(--mono);
    white-space: pre;
    overflow: auto;
    border-radius: 4px;
  }
  .editor-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 15px 20px;
    border-top: 1px solid var(--border);
  }
  .editor-actions > span {
    font-size: 12px;
    color: #667382;
  }
  .editor-actions .button {
    font-size: 12px;
  }
  .editor-status {
    margin: 0;
    padding: 0 20px 18px;
    font-size: 12px;
    color: #708bac;
    line-height: 1.7;
  }
  .output-label {
    padding: 6px 20px 14px;
  }
  .code-block {
    max-height: 300px;
  }
  .empty-state {
    padding: 32px 26px;
    min-height: 310px;
    color: #83a9d8;
  }
  .empty-state h3 {
    color: #3e587b;
  }
  .empty-state p {
    font-size: 12px;
  }
  .foundation-controls {
    padding: 10px 24px 22px;
  }
  .foundation-controls label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: #5d738f;
    margin: 0 0 12px;
  }
  .foundation-controls input[type='range'] {
    accent-color: #79acec;
    width: 100%;
    margin: 0 0 23px;
  }
  .foundation-controls input[type='number'],
  select {
    display: block;
    width: 100%;
    background: #f6f9fd;
    border: 1px solid #d9e4f2;
    border-radius: 4px;
    padding: 10px;
    color: #567397;
    font: 12px var(--mono);
    margin-bottom: 25px;
  }
  .foundation-controls p {
    color: #667385;
    font-size: 12px;
    line-height: 1.8;
  }
  .spin-illustration {
    padding: 0 24px 28px;
    text-align: center;
  }
  .spin-illustration svg {
    width: 100%;
    max-height: 250px;
    display: block;
  }
  .spin-illustration svg text {
    fill: #8494ac;
    font: 12px var(--mono);
  }
  .spin-illustration .mono {
    color: #8f78b3;
    font-size: 12px;
  }
  .spin-illustration .mono span {
    color: #756e7f;
    margin: 0 12px;
  }
  .spin-illustration > span {
    color: #687382;
    font-size: 12px;
  }
  .state-grid {
    padding: 5px 24px 20px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
  }
  .state-grid button {
    border: 1px solid #dde6f1;
    min-height: 68px;
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 9px;
    background: #f7f9fd;
    color: #6a83a2;
  }
  .state-grid button:hover {
    border-color: #88b4e6;
  }
  .state-grid button.marked {
    border-color: #73b8e3;
    background: #e9f6ff;
    color: #2679a6;
  }
  .state-grid button > span {
    font: 12px var(--mono);
  }
  .state-grid i {
    font: 12px var(--mono);
    letter-spacing: normal;
    color: #97a9bf;
  }
  .state-grid .marked i {
    color: #428aba;
  }
  .state-note {
    margin: 0;
    padding: 0 24px 22px;
    color: #657385;
    font-size: 12px;
    line-height: 1.7;
  }
  .marked-label {
    padding-top: 3px;
  }
  .marked-label strong {
    display: block;
    color: var(--cyan);
    font: 31px var(--mono);
    margin: 17px 0 24px;
  }
  .integration-row {
    display: grid;
    grid-template-columns: 1.6fr 1fr;
    gap: 20px;
    margin-top: 24px;
  }
  .comparison-plan {
    padding: 0 24px 20px;
  }
  .comparison-plan > div {
    display: flex;
    align-items: flex-start;
    gap: 18px;
    margin: 14px 0 22px;
  }
  .comparison-plan .mono {
    color: #8ca8ca;
    font-size: 12px;
    padding-top: 3px;
  }
  .comparison-plan p {
    margin: 0;
    font-size: 12px;
    color: #647386;
    line-height: 1.8;
  }
  .comparison-plan strong {
    display: block;
    color: #384f71;
    font-size: 12px;
    font-weight: 400;
    margin-bottom: 5px;
  }
  .next-workspace {
    border-top: 1px solid #dce8f7;
    padding: 24px 8px;
  }
  .next-workspace > :global(svg) {
    display: block;
    color: #5b9bd8;
    margin: 25px 0 18px;
  }
  .next-workspace h2 {
    font-weight: 400;
    font-size: 24px;
    letter-spacing: normal;
    line-height: 1.3;
  }
  .next-workspace p {
    color: #657385;
    font-size: 12px;
    line-height: 1.8;
    max-width: 280px;
    margin-bottom: 22px;
  }
  @media (max-width: 800px) {
    .foundation-grid,
    .compiler-grid,
    .integration-row {
      grid-template-columns: 1fr;
    }
    .page-heading :global(.badge) {
      margin-top: 20px;
    }
    .editor-actions {
      flex-wrap: wrap;
    }
  }
  @media (max-width: 400px) {
    .state-grid {
      gap: 6px;
      padding-inline: 15px;
    }
    .state-grid button > span {
      font-size: 12px;
    }
  }
</style>
