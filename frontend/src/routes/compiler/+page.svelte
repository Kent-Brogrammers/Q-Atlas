<script lang="ts">
  import { onDestroy } from 'svelte';
  import Icon from '#lib/components/Icon.svelte';
  import Panel from '#lib/components/Panel.svelte';
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

<svelte:head><title>Python Compiler · Q-Atlas</title></svelte:head>

<header class="page-heading">
  <div>
    <h1>Python Compiler</h1>
    <p>Convert a marked Python objective and download your generated script.</p>
  </div>
</header>

<p class="availability">
  <Icon name="info" size={17} />
  <span
    ><strong>Source conversion available.</strong> Your Python is parsed and verified without execution.
    Quantum execution stays disabled.</span
  >
</p>

<div class="compiler-layout">
  <aside aria-label="Compiler configuration">
    <Panel title="Configuration" subtitle="Load a script or start with an example">
      <div class="configuration">
        <fieldset>
          <legend>Source file</legend>
          <div class="file-picker" class:disabled={reading}>
            <input
              class="sr-only"
              id="objective-file"
              type="file"
              accept=".py,text/plain,text/x-python"
              disabled={reading}
              onchange={loadFile}
            />
            <label class="button" for="objective-file"
              >Load a .py file<Icon name="plus" size={15} /></label
            >
          </div>
          <p class="field-note">Or paste directly into the editor. Up to 20,000 characters.</p>
        </fieldset>
        <fieldset>
          <legend>Example</legend>
          <label for="program-example">Python program</label>
          <select id="program-example" bind:value={example} disabled={busy}>
            <option value="default">Ordinary Python · one decorator</option>
            {#each PROGRAM_EXAMPLES as item}<option value={item.filename}>{item.label}</option
              >{/each}
          </select>
          <button
            class="button"
            disabled={busy}
            onclick={() => {
              const selected = PROGRAM_EXAMPLES.find((item) => item.filename === example);
              replaceSource(
                selected?.source ?? DEFAULT_SCRIPT,
                selected?.filename ?? 'selection.py'
              );
            }}>Load example<Icon name="reset" size={15} /></button
          >
        </fieldset>
        <div class="marker-guide">
          <h3>Mark your objective</h3>
          <p>
            Put <code>@qatlas.objective</code> above the function you want to convert. Keep your function
            and input names. No circuit code is required.
          </p>
        </div>
        <details class="advanced-options">
          <summary>Advanced conversion options</summary>
          <div class="advanced-body">
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
            <p class="field-note">
              The default is one layer. If you have an existing zero-argument circuit factory, mark
              it with <code>@qatlas.circuit</code> to replace it. Otherwise the compiler adds the generated
              builder automatically.
            </p>
          </div>
        </details>
      </div>
    </Panel>
  </aside>

  <div class="compiler-workspace">
    <Panel title="Your Python script" subtitle="Keep your Python. Mark what to convert.">
      {#snippet toolbar()}<span class="file-type">Python · .py</span>{/snippet}
      <div class="source-editor">
        <div class="editor-heading">
          <label for="source">Python source</label>
          <span class="file-name" title={fileName}>{fileName}</span>
        </div>
        <textarea
          id="source"
          bind:this={editor}
          value={source}
          rows="17"
          maxlength={MAX_SOURCE_LENGTH}
          spellcheck="false"
          aria-describedby="source-scope"
          oninput={(event) => {
            source = event.currentTarget.value;
            fileName = 'Pasted source';
            invalidate();
          }}
        ></textarea>
        <div class="editor-footer">
          <span class="character-count">{source.length.toLocaleString()} / 20,000 characters</span>
          <button
            class="button primary"
            disabled={busy || !source.trim()}
            onclick={() => run('generate')}
          >
            {loading === 'generate' ? 'Converting…' : 'Convert Python'}<Icon
              name="arrow"
              size={15}
            />
          </button>
        </div>
        <p class="field-note" id="source-scope">
          Supports binary optimization objectives with 1–6 inputs. The surrounding program stays in
          place.
        </p>
      </div>
    </Panel>

    <div
      class="request-status"
      class:has-status={reading || loading === 'plan' || !!error}
      aria-live="polite"
      aria-busy={busy}
    >
      {#if reading}<p role="status" class="availability">
          <Icon name="clock" size={17} />Reading the selected file as text…
        </p>{/if}
      {#if loading === 'plan'}<p role="status" class="availability">
          <Icon name="clock" size={17} />Preparing a comparison without execution…
        </p>{/if}
      {#if error}<p role="alert" class="availability error-notice">
          <Icon name="info" size={17} /><span>{error}</span>
        </p>{/if}
    </div>

    <Panel
      title="Converted script"
      subtitle={artifact
        ? 'Generated and verified · not executed'
        : analysis?.status === 'rejected'
          ? 'Conversion needs attention'
          : 'Your output will appear here'}
    >
      {#snippet toolbar()}
        {#if generatedUrl}<a
            class="button primary"
            href={generatedUrl}
            download={generatedFilename(fileName)}
          >
            Download .py<Icon name="download" size={15} /></a
          >{/if}
      {/snippet}
      {#if artifact}
        <div class="output-body">
          <p role="status">
            Your program and function names are preserved.
            {#if artifact.replaced_function}The marked {artifact.replaced_function}() factory was
              replaced.
            {:else}The generated builder was added automatically.{/if}
          </p>
          <p class="field-note">
            Automatic quantum execution will be connected through the shared runtime; it is disabled
            today.
          </p>
        </div>
        <details class="result-disclosure">
          <summary>Preview Python</summary>
          <div class="preview-body">
            <label class="sr-only" for="generated-python">Generated Python source</label>
            <textarea
              id="generated-python"
              readonly
              value={artifact.source}
              rows="18"
              spellcheck="false"
            ></textarea>
          </div>
        </details>
      {:else if analysis?.status === 'rejected'}
        <div class="output-body rejection" role="status">
          <h3>This region is not supported yet</h3>
          <p>
            Keep the ordinary script around the marked function. The marked region currently needs
            bounded binary arithmetic.
          </p>
          <ul class="diagnostics">
            {#each analysis.diagnostics as diagnostic}
              <li>
                <p>{diagnostic.message}</p>
                {#if diagnostic.line}<button
                    class="button small"
                    onclick={() => selectLine(diagnostic.line!)}
                  >
                    Line {diagnostic.line}<Icon name="arrow" size={13} /></button
                  >{/if}
              </li>
            {/each}
          </ul>
        </div>
      {:else}
        <div class="output-placeholder">
          <Icon name={loading === 'generate' ? 'clock' : 'code'} size={24} />
          <div>
            <h3>
              {loading === 'generate' ? 'Converting your source…' : 'Ready when your script is'}
            </h3>
            <p>
              Load or paste Python, mark your objective, then select <strong>Convert Python</strong
              >. The converted .py file will be available to preview and download.
            </p>
          </div>
        </div>
      {/if}
    </Panel>

    {#if analysis?.status === 'supported'}
      <details class="panel conversion-details">
        <summary>Conversion details and future benchmarking</summary>
        <div class="detail-section">
          {#each analysis.diagnostics as diagnostic}
            <p class="diagnostic-note"><strong>{diagnostic.code}</strong> {diagnostic.message}</p>
          {/each}
        </div>
        {#if analysis.qubo}
          <div class="detail-section">
            <h3>Extracted objective</h3>
            <p>
              Original sense: {analysis.qubo.original_sense ?? 'minimize'} · Canonical solver sense: minimize
              · Constant: {analysis.qubo.constant ?? 0}
            </p>
            <p>
              Declared input order maps to canonical bit indices; names are not sorted
              alphabetically.
            </p>
            <div class="coefficient-tables">
              <div class="table-scroll">
                <table>
                  <caption>Linear coefficients</caption>
                  <thead
                    ><tr><th scope="col">Canonical bit</th><th scope="col">Coefficient</th></tr
                    ></thead
                  >
                  <tbody>
                    {#each analysis.qubo.linear as coefficient, index}<tr
                        ><td>{index}</td><td>{coefficient}</td></tr
                      >{/each}
                  </tbody>
                </table>
              </div>
              <div class="table-scroll">
                <table>
                  <caption>Pair coefficients</caption>
                  <thead><tr><th scope="col">Bits</th><th scope="col">Coefficient</th></tr></thead>
                  <tbody>
                    {#each analysis.qubo.quadratic ?? [] as term}<tr
                        ><td>{term.i}, {term.j}</td><td>{term.coefficient}</td></tr
                      >
                    {:else}<tr><td colspan="2">No pair terms</td></tr>{/each}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        {/if}
        {#if analysis.circuit}
          <details class="result-disclosure">
            <summary>Generated circuit plan · not executed</summary>
            <div class="detail-section">
              <p>
                {analysis.circuit.num_qubits} qubits · {analysis.circuit.p} layers · Logical depth {analysis
                  .circuit.logical_depth}. Transpiled depth is unavailable.
              </p>
              <p>Parameter order: {analysis.circuit.parameters.join(', ')}</p>
              <div class="table-scroll">
                <table>
                  <caption>Ordered gates</caption>
                  <thead
                    ><tr
                      ><th scope="col">Gate</th><th scope="col">Qubits</th><th scope="col">Angle</th
                      ></tr
                    ></thead
                  >
                  <tbody>
                    {#each analysis.circuit.gates as gate}<tr>
                        <td>{gate.name}</td><td>{gate.qubits.join(', ')}</td>
                        <td>{gate.angle ? formatAngle(gate.angle) : '—'}</td>
                      </tr>{/each}
                  </tbody>
                </table>
              </div>
              <p>Global phase: {analysis.circuit.global_phase.map(formatAngle).join(' + ')}</p>
            </div>
          </details>
        {/if}
        <div class="detail-section">
          <h3>Future comparison</h3>
          <p>
            Both future solvers optimize the same verified objective. This does not run or time the
            surrounding Python application.
          </p>
          <div class="comparison-actions">
            <button class="button" disabled={busy} onclick={() => run('plan')}
              >Prepare comparison<Icon name="arrow" size={15} /></button
            >
            <button class="button" disabled>Run comparison — execution disabled</button>
          </div>
          {#if plan}
            <div class="comparison-plan">
              <p role="status"><strong>Comparison prepared · not executed</strong></p>
              <p>
                Layers {plan.config.p} · Shots {plan.config.shots} · Seed {plan.config.seed}.
                Classical and QAOA execution are disabled.
              </p>
              {#if planUrl}<a class="button" href={planUrl} download="q_atlas_benchmark_plan.json">
                  Download comparison plan<Icon name="download" size={15} /></a
                >{/if}
              <ul class="blockers">
                {#each plan.blockers as blocker}<li>{blocker}</li>{/each}
              </ul>
            </div>
          {/if}
        </div>
        <details class="result-disclosure">
          <summary>Raw analysis JSON</summary>
          <pre class="code-block">{JSON.stringify(analysis, null, 2)}</pre>
        </details>
      </details>
    {/if}
  </div>
</div>

<style>
  .availability {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 14px 16px;
    margin: 0 0 24px;
    border-left: 3px solid var(--blue);
    background: #f4f7fc;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
  }
  .availability :global(svg) {
    margin-top: 2px;
    color: var(--blue);
  }
  .availability strong {
    color: var(--text);
    font-weight: 500;
  }
  .compiler-layout {
    display: grid;
    grid-template-columns: 290px minmax(0, 1fr);
    gap: 24px;
    align-items: start;
  }
  aside,
  .compiler-workspace {
    min-width: 0;
  }
  .compiler-workspace {
    display: grid;
    gap: 20px;
  }
  .configuration {
    padding: 0 24px 20px;
  }
  fieldset {
    padding: 0;
    margin: 0 0 20px;
    border: 0;
    min-width: 0;
  }
  legend {
    width: 100%;
    border-top: 1px solid var(--border);
    padding: 16px 0 12px;
    font-size: 13px;
    font-weight: 500;
  }
  fieldset:first-child legend {
    border: 0;
    padding-top: 0;
  }
  label {
    display: block;
    font-size: 12px;
    margin-bottom: 7px;
    color: #46546a;
  }
  select {
    display: block;
    width: 100%;
    min-height: 40px;
    min-width: 0;
    padding: 9px 10px;
    margin-bottom: 14px;
    background: #f8fafd;
    border: 1px solid #dbe1e9;
    border-radius: 2px;
    color: var(--text);
    font-size: 12px;
  }
  select:disabled {
    color: var(--muted);
  }
  .configuration .button {
    width: 100%;
    font-size: 13px;
  }
  .file-picker label {
    display: inline-flex;
    margin: 0;
    cursor: pointer;
  }
  .file-picker:focus-within label {
    outline: 2px solid var(--blue);
    outline-offset: 4px;
  }
  .file-picker.disabled label {
    cursor: default;
    opacity: 0.5;
  }
  .field-note {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
    margin: 12px 0 0;
  }
  .marker-guide {
    border-top: 1px solid var(--border);
    padding-top: 16px;
  }
  h3 {
    margin: 0 0 9px;
    font-size: 13px;
    font-weight: 500;
  }
  .marker-guide p {
    margin: 0;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.7;
  }
  code {
    font-family: var(--mono);
    overflow-wrap: anywhere;
  }
  summary {
    cursor: pointer;
    font-size: 13px;
  }
  .advanced-options {
    margin-top: 20px;
    border-top: 1px solid var(--border);
    padding-top: 16px;
    color: var(--muted);
  }
  .advanced-body {
    padding-top: 16px;
  }
  .advanced-body select {
    margin-bottom: 0;
  }
  .file-type {
    color: var(--muted);
    font: 11px/1.6 var(--mono);
  }
  .source-editor {
    padding: 0 24px 20px;
  }
  .editor-heading,
  .editor-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }
  .editor-heading {
    padding: 10px 12px;
    background: #f8fafd;
    border: 1px solid var(--border);
    border-bottom: 0;
  }
  .editor-heading label {
    margin: 0;
    flex-shrink: 0;
  }
  .file-name {
    font: 11px/1.6 var(--mono);
    color: var(--muted);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  textarea {
    display: block;
    width: 100%;
    min-width: 0;
    padding: 16px;
    margin: 0;
    border: 1px solid var(--border);
    border-radius: 0;
    color: #38567a;
    font: 12px/1.85 var(--mono);
    resize: vertical;
    background: #f8fafd;
    tab-size: 4;
  }
  .editor-footer {
    flex-wrap: wrap;
    padding-top: 16px;
  }
  .character-count {
    color: var(--muted);
    font: 11px/1.6 var(--mono);
  }
  .request-status:not(.has-status) {
    display: none;
  }
  .request-status .availability {
    margin: 0;
  }
  .error-notice {
    border-left-color: #a87930;
    background: #fffaf0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .error-notice :global(svg) {
    color: #a87930;
  }
  .output-body,
  .output-placeholder {
    padding: 0 24px 20px;
  }
  .output-body > p,
  .output-placeholder p,
  .detail-section p {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.7;
    margin: 0 0 12px;
  }
  .output-body > .field-note {
    font-size: 12px;
    margin-bottom: 0;
  }
  .output-placeholder {
    border-top: 1px solid var(--border);
    padding-top: 24px;
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }
  .output-placeholder > :global(svg) {
    color: var(--subtle);
  }
  .output-placeholder p {
    max-width: 520px;
    margin: 0;
  }
  .output-placeholder strong {
    font-weight: 500;
    color: var(--text);
  }
  .result-disclosure {
    border-top: 1px solid var(--border);
  }
  .result-disclosure > summary {
    padding: 17px 24px;
  }
  .preview-body {
    padding: 0 24px 24px;
  }
  .conversion-details > summary {
    padding: 20px 24px;
    font-size: 14px;
    font-weight: 500;
  }
  .detail-section {
    padding: 0 24px 20px;
    overflow-wrap: anywhere;
  }
  .detail-section + .detail-section {
    border-top: 1px solid var(--border);
    padding-top: 20px;
  }
  .coefficient-tables {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 16px;
  }
  .table-scroll {
    min-width: 0;
    overflow-x: auto;
    margin-bottom: 16px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    text-align: left;
    font-size: 12px;
  }
  caption {
    text-align: left;
    padding: 0 0 12px;
    color: var(--muted);
  }
  th,
  td {
    padding: 12px 16px;
    border-block: 1px solid var(--border);
    white-space: nowrap;
  }
  th {
    font-weight: 400;
  }
  thead {
    background: #f8fafd;
    color: var(--muted);
  }
  td {
    font-family: var(--mono);
  }
  .comparison-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .comparison-plan {
    margin-top: 20px;
    border-left: 3px solid var(--blue);
    background: #f4f7fc;
    padding: 16px;
  }
  .blockers,
  .diagnostics {
    list-style: disc;
    padding-left: 18px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.7;
    margin: 16px 0 0;
  }
  .diagnostics li + li {
    margin-top: 16px;
  }
  .diagnostics p {
    margin: 0 0 8px;
    overflow-wrap: anywhere;
  }
  pre {
    max-height: 320px;
  }
  @media (max-width: 950px) {
    .compiler-layout {
      grid-template-columns: 1fr;
    }
    .configuration {
      display: grid;
      grid-template-columns: 1fr 1fr;
      column-gap: 24px;
      align-items: start;
    }
    fieldset:nth-child(2) legend {
      border: 0;
      padding-top: 0;
    }
    .marker-guide,
    .advanced-options {
      grid-column: 1 / -1;
    }
  }
  @media (max-width: 600px) {
    .configuration {
      display: block;
    }
    fieldset:nth-child(2) legend {
      border-top: 1px solid var(--border);
      padding-top: 16px;
    }
    .configuration,
    .source-editor,
    .output-body,
    .output-placeholder,
    .preview-body,
    .detail-section,
    .result-disclosure > summary,
    .conversion-details > summary {
      padding-inline: 18px;
    }
    .coefficient-tables {
      grid-template-columns: 1fr;
    }
    .editor-footer {
      align-items: stretch;
      flex-direction: column;
    }
    .comparison-actions .button {
      width: 100%;
    }
    .file-type {
      display: none;
    }
  }
</style>
