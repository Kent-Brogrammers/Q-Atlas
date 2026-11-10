<script lang="ts">
  import { onDestroy } from 'svelte';
  import { api, ApiError } from '../../api/client.ts';
  import type {
    CompilerAnalyzeResult,
    GeneratedPythonArtifact,
    CompilerBenchmarkPlan
  } from '../../types/index.ts';
  import {
    DEFAULT_SCRIPT,
    MAX_SOURCE_LENGTH,
    readObjectiveFile,
    generatedFilename,
    formatAngle
  } from '../../compiler/source.ts';
  import { PROGRAM_EXAMPLES } from '../../compiler/examples.ts';

  let source = $state(DEFAULT_SCRIPT);
  let fileName = $state('selection.py');
  let example = $state('default');
  let layers = $state(1);
  let analysis = $state<CompilerAnalyzeResult>();
  let artifact = $state<GeneratedPythonArtifact>();
  let plan = $state<CompilerBenchmarkPlan>();
  let error = $state('');
  let loading = $state<'generate' | 'plan' | null>(null);
  let reading = $state(false);
  let generatedUrl = $state('');
  let planUrl = $state('');
  let editor = $state<HTMLTextAreaElement>();
  let revision = 0;
  let readSequence = 0;
  let active = true;
  const busy = $derived(loading !== null || reading);

  onDestroy(() => {
    active = false;
    revision++;
    readSequence++;
  });
  $effect(() => {
    generatedUrl = '';
    if (!artifact) return;
    const url = URL.createObjectURL(
      new Blob([artifact.source], { type: 'text/x-python;charset=utf-8' })
    );
    generatedUrl = url;
    return () => URL.revokeObjectURL(url);
  });
  $effect(() => {
    planUrl = '';
    if (!plan) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(plan, null, 2) + '\n'], { type: 'application/json' })
    );
    planUrl = url;
    return () => URL.revokeObjectURL(url);
  });

  function invalidate() {
    revision++;
    analysis = undefined;
    artifact = undefined;
    plan = undefined;
    error = '';
  }
  function replaceSource(text: string, name: string) {
    invalidate();
    source = text;
    fileName = name;
  }
  async function loadFile(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    invalidate();
    const currentRevision = revision;
    const currentRead = ++readSequence;
    reading = true;
    try {
      const text = await readObjectiveFile(file);
      if (active && revision === currentRevision && readSequence === currentRead)
        replaceSource(text, file.name);
    } catch (caught) {
      if (active && revision === currentRevision && readSequence === currentRead)
        error = caught instanceof Error ? caught.message : 'Could not read this file.';
    } finally {
      if (active && readSequence === currentRead) reading = false;
    }
  }
  async function run(kind: 'generate' | 'plan') {
    if (busy || !source.trim() || (kind === 'plan' && analysis?.status !== 'supported')) return;
    const currentRevision = revision;
    loading = kind;
    error = '';
    plan = undefined;
    if (kind === 'generate') {
      analysis = undefined;
      artifact = undefined;
    }
    try {
      if (kind === 'generate') {
        const result = await api.generateScript({ source, p: layers });
        if (active && revision === currentRevision) {
          analysis = result;
          artifact = result.artifact ?? undefined;
        }
      } else {
        const result = await api.prepareCompilerBenchmark({ source, config: { p: layers } });
        if (active && revision === currentRevision) plan = result;
      }
    } catch (caught) {
      if (active && revision === currentRevision) {
        error =
          caught instanceof ApiError
            ? [
                caught.message,
                ...(caught.body.error.diagnostics ?? []).map((item) => item.message)
              ].join('\n')
            : caught instanceof Error
              ? caught.message
              : 'Could not reach the API.';
      }
    } finally {
      if (active) loading = null;
    }
  }
  function selectLine(line: number) {
    const start =
      line <= 1
        ? 0
        : source
            .split('\n')
            .slice(0, line - 1)
            .join('\n').length + 1;
    const end = source.indexOf('\n', start);
    editor?.focus();
    editor?.setSelectionRange(start, end < 0 ? source.length : end);
  }
</script>

<svelte:head><title>Python compiler · Q-Atlas</title></svelte:head>
<header class="page-heading">
  <div>
    <p class="eyebrow">Python compiler</p>
    <h1>Keep your Python. Mark what to convert.</h1>
    <p>
      Load a script and put <code>@qatlas.objective</code> above your objective function. Function and
      input names are yours; no circuit code is required.
    </p>
  </div>
</header>

<section class="panel compiler-panel" aria-labelledby="source-heading">
  <h2 id="source-heading">Your Python script</h2>
  <div class="controls">
    <label
      >Load a .py file<input
        id="objective-file"
        type="file"
        accept=".py,text/plain,text/x-python"
        disabled={reading}
        onchange={loadFile}
      /></label
    >
    <label
      >Example<select id="program-example" bind:value={example} disabled={busy}>
        <option value="default">Ordinary Python · one decorator</option>
        {#each PROGRAM_EXAMPLES as item}<option value={item.filename}>{item.label}</option>{/each}
      </select></label
    >
    <button
      class="button small"
      disabled={busy}
      onclick={() => {
        const selected = PROGRAM_EXAMPLES.find((item) => item.filename === example);
        replaceSource(selected?.source ?? DEFAULT_SCRIPT, selected?.filename ?? 'selection.py');
      }}>Load example</button
    >
  </div>
  <label for="source">Python source</label>
  <textarea
    id="source"
    bind:this={editor}
    value={source}
    rows="17"
    maxlength={MAX_SOURCE_LENGTH}
    spellcheck="false"
    oninput={(event) => {
      source = event.currentTarget.value;
      fileName = 'Pasted source';
      invalidate();
    }}
  ></textarea>
  <p class="muted small">{fileName} · {source.length.toLocaleString()} / 20,000 characters</p>
  <button class="button primary" disabled={busy || !source.trim()} onclick={() => run('generate')}
    >{loading === 'generate' ? 'Converting…' : 'Convert Python'}</button
  >
  <p class="muted small">
    Currently converts binary optimization objectives with 1–6 inputs. The rest of your program
    stays in place. Source is never executed here.
  </p>
  <details>
    <summary>Advanced conversion options</summary>
    <label for="circuit-layers">Circuit layers</label>
    <select
      id="circuit-layers"
      value={layers}
      disabled={busy}
      onchange={(event) => {
        layers = Number(event.currentTarget.value);
        invalidate();
      }}
    >
      {#each Array.from({ length: 8 }, (_, i) => i + 1) as count}<option value={count}
          >{count}</option
        >{/each}
    </select>
    <p class="small muted">
      The default is one layer. Only if you already have circuit code, mark its zero-argument
      factory with <code>@qatlas.circuit</code> to replace it. Otherwise the compiler adds the generated
      builder automatically.
    </p>
  </details>
</section>

<div aria-live="polite" aria-busy={busy}>
  {#if reading}<p role="status">Reading the selected file as text…</p>{/if}
  {#if loading === 'plan'}<p role="status">Preparing a comparison without execution…</p>{/if}
  {#if error}<p role="alert" class="notice">{error}</p>{/if}
  {#if analysis?.status === 'rejected'}
    <section class="panel compiler-panel" aria-labelledby="rejection-heading">
      <h2 id="rejection-heading">This region is not supported yet</h2>
      <p>
        Keep the ordinary script around the marked function. The marked region currently needs
        bounded binary arithmetic.
      </p>
      {#each analysis.diagnostics as diagnostic}
        <p>{diagnostic.message}</p>
        {#if diagnostic.line}<button
            class="button small"
            onclick={() => selectLine(diagnostic.line!)}>Line {diagnostic.line}</button
          >{/if}
      {/each}
    </section>
  {/if}
</div>

{#if artifact}
  <section class="panel compiler-panel" aria-labelledby="download-heading">
    <div class="section-heading">
      <h2 id="download-heading">Converted script</h2>
      {#if generatedUrl}<a
          class="button primary"
          href={generatedUrl}
          download={generatedFilename(fileName)}>Download .py</a
        >{/if}
    </div>
    <p>
      Your program and function names are preserved. {artifact.replaced_function
        ? `The marked ${artifact.replaced_function}() factory was replaced.`
        : 'The generated builder was added automatically.'}
    </p>
    <p class="small muted">
      Generated and verified, not executed. Automatic quantum execution will be connected through
      the shared runtime; it is disabled today.
    </p>
    <details>
      <summary>Preview Python</summary><label for="generated-python">Generated Python source</label
      ><textarea id="generated-python" readonly value={artifact.source} rows="18" spellcheck="false"
      ></textarea>
    </details>
  </section>
{/if}

{#if analysis?.status === 'supported'}
  <details class="panel compiler-panel">
    <summary>Conversion details and future benchmarking</summary>
    {#each analysis.diagnostics as diagnostic}<p class="small">
        <strong>{diagnostic.code}</strong>
        {diagnostic.message}
      </p>{/each}
    {#if analysis.qubo}
      <h2>Extracted objective</h2>
      <p class="small muted">
        Original sense: {analysis.qubo.original_sense ?? 'minimize'} · Canonical solver sense: minimize
        · Constant: {analysis.qubo.constant ?? 0}
      </p>
      <p class="small muted">
        Declared input order maps to canonical bit indices; names are not sorted alphabetically.
      </p>
      <table>
        <caption>Linear coefficients</caption><thead
          ><tr><th>Canonical bit</th><th>Coefficient</th></tr></thead
        ><tbody>
          {#each analysis.qubo.linear as coefficient, index}<tr
              ><td>{index}</td><td>{coefficient}</td></tr
            >{/each}
        </tbody>
      </table>
      <table>
        <caption>Pair coefficients</caption><thead><tr><th>Bits</th><th>Coefficient</th></tr></thead
        ><tbody>
          {#each analysis.qubo.quadratic ?? [] as term}<tr
              ><td>{term.i}, {term.j}</td><td>{term.coefficient}</td></tr
            >{/each}
        </tbody>
      </table>
    {/if}
    {#if analysis.circuit}
      <details>
        <summary>Generated circuit plan · not executed</summary>
        <p class="small">
          {analysis.circuit.num_qubits} qubits · {analysis.circuit.p} layers · Logical depth {analysis
            .circuit.logical_depth}. Transpiled depth is unavailable.
        </p>
        <p class="small">Parameter order: {analysis.circuit.parameters.join(', ')}</p>
        <div class="table-scroll">
          <table>
            <caption>Ordered gates</caption><thead
              ><tr><th>Gate</th><th>Qubits</th><th>Angle</th></tr></thead
            ><tbody>
              {#each analysis.circuit.gates as gate}<tr
                  ><td>{gate.name}</td><td>{gate.qubits.join(', ')}</td><td
                    >{gate.angle ? formatAngle(gate.angle) : '—'}</td
                  ></tr
                >{/each}
            </tbody>
          </table>
        </div>
        <p class="small">
          Global phase: {analysis.circuit.global_phase.map(formatAngle).join(' + ')}
        </p>
      </details>
    {/if}
    <h2>Future comparison</h2>
    <p class="small">
      Both future solvers optimize the same verified objective. This does not run or time the
      surrounding Python application.
    </p>
    <button class="button" disabled={busy} onclick={() => run('plan')}>Prepare comparison</button>
    {#if plan}
      <p role="status">Comparison prepared · not executed</p>
      <p class="small">
        Layers {plan.config.p} · Shots {plan.config.shots} · Seed {plan.config.seed}. Classical and
        QAOA execution are disabled.
      </p>
      {#if planUrl}<a class="button" href={planUrl} download="q_atlas_benchmark_plan.json"
          >Download comparison plan</a
        >{/if}
      <ul>
        {#each plan.blockers as blocker}<li class="small muted">{blocker}</li>{/each}
      </ul>
    {/if}
    <button class="button" disabled>Run comparison — execution disabled</button>
    <details>
      <summary>Raw analysis JSON</summary>
      <pre class="code-block">{JSON.stringify(analysis, null, 2)}</pre>
    </details>
  </details>
{/if}

<style>
  .compiler-panel {
    padding: 22px;
    margin-bottom: 18px;
  }
  h2 {
    font-size: 17px;
    font-weight: 500;
    margin: 0 0 12px;
  }
  p {
    line-height: 1.6;
  }
  .small {
    font-size: 13px;
  }
  .controls,
  .section-heading {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    margin-bottom: 14px;
  }
  .section-heading {
    justify-content: space-between;
  }
  .section-heading h2 {
    margin: 0;
  }
  label {
    display: block;
    font-size: 13px;
    min-width: 0;
    max-width: 100%;
  }
  input,
  select {
    display: block;
    max-width: 100%;
    margin: 6px 0;
    border: 1px solid var(--border);
    padding: 8px;
    background: white;
  }
  textarea {
    display: block;
    width: 100%;
    min-width: 0;
    padding: 14px;
    margin-top: 8px;
    border: 1px solid var(--border);
    border-radius: 4px;
    font: 13px/1.6 var(--mono);
    resize: vertical;
    background: white;
  }
  details {
    margin-top: 18px;
  }
  summary {
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 12px;
  }
  .notice {
    padding: 16px;
    background: #fff7e8;
    white-space: pre-wrap;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin: 12px 0;
  }
  th,
  td {
    text-align: left;
    border-bottom: 1px solid var(--border);
    padding: 8px;
  }
  caption {
    text-align: left;
    font-weight: 500;
    margin-bottom: 6px;
  }
  .table-scroll {
    overflow: auto;
  }
  pre {
    overflow: auto;
    max-height: 320px;
  }
  code {
    font-family: var(--mono);
  }
  @media (max-width: 600px) {
    .compiler-panel {
      padding: 16px;
    }
  }
</style>
