<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import Icon from '#lib/components/Icon.svelte';
  import Panel from '#lib/components/Panel.svelte';
  import OptimizationWorkspace from '#lib/components/OptimizationWorkspace.svelte';
  import ComparisonResult from '#lib/components/ComparisonResult.svelte';
  import HardwareAnalytics from '#lib/components/HardwareAnalytics.svelte';
  import { api } from '../../api/client.ts';
  import { compilerErrorMessage } from '../../compiler/errors.ts';
  import type {
    CompilerAnalyzeResult,
    GeneratedPythonArtifact,
    CompilerBenchmarkResult,
    OptimizationResult,
    HardwareJob
  } from '../../types/index.ts';
  import {
    DEFAULT_SCRIPT,
    DEFAULT_FILENAME,
    MAX_SOURCE_LENGTH,
    readObjectiveFile,
    generatedFilename
  } from '../../compiler/source.ts';
  import { PROGRAM_EXAMPLES } from '../../compiler/examples.ts';
  const steps = [
    { id: 'input', label: '1. Python input' },
    { id: 'run', label: '2. Run' },
    { id: 'results', label: '3. Results' }
  ] as const;
  type Step = (typeof steps)[number]['id'];
  let step = $state<Step>('input');
  let source = $state(DEFAULT_SCRIPT);
  let fileName = $state(DEFAULT_FILENAME);
  let example = $state<string>(DEFAULT_FILENAME);
  let layers = $state(1);
  let analysis = $state<CompilerAnalyzeResult>();
  let artifact = $state<GeneratedPythonArtifact>();
  let localResult = $state<CompilerBenchmarkResult | OptimizationResult | null>(null);
  let physicalResult = $state<HardwareJob | null>(null);
  let error = $state('');
  let loading = $state<'generate' | null>(null);
  let reading = $state(false);
  let editor = $state<HTMLTextAreaElement>();
  let revision = 0;
  let active = true;
  let generatedUrl = $state('');
  const busy = $derived(!!loading || reading);
  const hasResults = $derived(!!localResult || !!physicalResult);
  $effect(() => {
    if (!artifact) {
      generatedUrl = '';
      return;
    }
    const url = URL.createObjectURL(new Blob([artifact.source], { type: 'text/x-python' }));
    generatedUrl = url;
    return () => URL.revokeObjectURL(url);
  });
  onDestroy(() => {
    active = false;
    revision++;
  });
  function invalidate() {
    revision++;
    artifact = undefined;
    analysis = undefined;
    localResult = null;
    physicalResult = null;
    error = '';
    step = 'input';
  }
  function replaceSource(text: string, name: string) {
    invalidate();
    source = text;
    fileName = name;
  }
  async function goToStep(target: Step) {
    step = target;
    await tick();
    document.getElementById('compiler-stage-title')?.focus();
  }
  async function loadFile(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    invalidate();
    const version = revision;
    reading = true;
    try {
      const text = await readObjectiveFile(file);
      if (active && version === revision) replaceSource(text, file.name);
    } catch (e) {
      if (active && version === revision)
        error = e instanceof Error ? e.message : 'Could not read file.';
    } finally {
      if (active) reading = false;
    }
  }
  async function run(_kind: 'generate') {
    if (busy || !source.trim()) return;
    loading = 'generate';
    error = '';
    const version = revision;
    try {
      const result = await api.generateScript({ source, p: layers });
      if (active && version === revision) {
        analysis = result;
        artifact = result.artifact ?? undefined;
        if (artifact) await goToStep('run');
      }
    } catch (e) {
      if (active && version === revision)
        error = compilerErrorMessage(e, 'Could not reach the API.');
    } finally {
      if (active) loading = null;
    }
  }
  function selectLine(line: number) {
    const start =
      source
        .split('\n')
        .slice(0, line - 1)
        .join('\n').length + (line > 1 ? 1 : 0);
    editor?.focus();
    editor?.setSelectionRange(
      start,
      source.indexOf('\n', start) < 0 ? source.length : source.indexOf('\n', start)
    );
  }
</script>

<svelte:head><title>Python Compiler · Q-Atlas</title></svelte:head>
<header class="page-heading">
  <div>
    <h1>Python Compiler</h1>
    <p>Choose your Python. Run a comparison. See what happened.</p>
  </div>
</header>
<nav class="workflow-nav" aria-label="Compiler workflow">
  {#each steps as item}<button
      class="button"
      class:primary={step === item.id}
      aria-current={step === item.id ? 'step' : undefined}
      disabled={busy || (item.id === 'run' && !artifact) || (item.id === 'results' && !hasResults)}
      onclick={() => goToStep(item.id)}>{item.label}</button
    >{/each}
</nav>
<h2 id="compiler-stage-title" tabindex="-1">
  {step === 'input'
    ? 'Start with your Python'
    : step === 'run'
      ? 'Run your compiled objective'
      : 'Your results'}
</h2>
{#if error}<p role="alert">{error}</p>{/if}
{#if reading}<p role="status">Reading file…</p>{/if}
{#if step === 'input'}
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
                  selected?.filename ?? DEFAULT_FILENAME
                );
              }}>Load example<Icon name="reset" size={15} /></button
            >
            <p class="field-note">
              Explore energy portfolios, dense weighted cuts, balanced workloads, or conflicting
              tasks. Each example uses one binary choice per qubit, with three to six qubits.
            </p>
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
                The default is one layer. If you have an existing zero-argument circuit factory,
                mark it with <code>@qatlas.circuit</code> to replace it. Otherwise the compiler adds the
                generated builder automatically.
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
            <span class="character-count">{source.length.toLocaleString()} / 20,000 characters</span
            >
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
            Supports binary optimization objectives with 1–6 inputs. The surrounding program stays
            in place.
          </p>
        </div>
      </Panel>

      {#if analysis?.status === 'rejected'}
        <Panel
          title="This region is not supported yet"
          subtitle="Update the marked objective and try again"
        >
          <div class="output-body" role="status">
            <p>
              Keep the ordinary script around the marked function. The marked region currently needs
              bounded binary arithmetic.
            </p>
            <ul class="diagnostics">
              {#each analysis.diagnostics as diagnostic}<li>
                  <p>{diagnostic.message}</p>
                  {#if diagnostic.line}<button
                      class="button small"
                      onclick={() => selectLine(diagnostic.line!)}
                      >Line {diagnostic.line}<Icon name="arrow" size={13} /></button
                    >{/if}
                </li>{/each}
            </ul>
          </div>
        </Panel>
      {/if}
      {#if artifact}
        <div class="step-actions">
          <p class="field-note">Your compiled code is saved for this source.</p>
          <button class="button" disabled={busy} onclick={() => goToStep('run')}
            >Continue to run<Icon name="arrow" size={15} /></button
          >
        </div>
      {/if}
    </div>
  </div>
{/if}
{#if artifact}
  <div hidden={step !== 'run'}>
    <p>
      Your code is ready. Choose where to run it, then press Run. Uploaded Python is parsed and
      validated; it is never executed.
    </p>
    <details>
      <summary>View or download the compiled Python</summary>
      <a class="button" href={generatedUrl} download={generatedFilename(fileName)}>Download .py</a>
      <textarea aria-label="Generated Python source" readonly value={artifact.source} rows="12"
      ></textarea>
    </details>
    <OptimizationWorkspace
      {source}
      onResult={(result) => {
        localResult = result;
        if (result) void goToStep('results');
      }}
      onHardwareResult={(job) => {
        if (!job) return;
        const finished =
          physicalResult?.request_id === job.request_id &&
          !physicalResult.measurement_complete &&
          job.measurement_complete;
        physicalResult = job;
        if (finished) void goToStep('results');
      }}
    />
    {#if physicalResult}<button class="button primary" onclick={() => goToStep('results')}
        >View QPU results &amp; status</button
      >{/if}
  </div>
{/if}
{#if step === 'results'}
  {#if physicalResult}
    <Panel
      title={physicalResult.measurement_complete ? 'Completed QPU result' : 'QPU job status'}
      subtitle={`${physicalResult.backend_name ?? 'IBM'} · ${physicalResult.job_id ?? 'Awaiting job ID'}`}
    >
      <div class="output-body">
        <p><strong>{physicalResult.status}</strong> · {physicalResult.created_at_utc}</p>
        <p>
          This saved job keeps its original inputs. Job input: {physicalResult.task.kind ===
          'compiler'
            ? physicalResult.task.parameters.source
            : 'Shared demonstration'}
        </p>
        {#if physicalResult.measurement_complete}<HardwareAnalytics job={physicalResult} />
        {:else}<p>
            Your job is still being processed. Its status updates automatically while this page is
            open.
          </p>{/if}
      </div>
    </Panel>
  {/if}
  {#if localResult}<Panel
      title="Local comparison completed"
      subtitle="Exact classical solver and Qiskit Aer"
      ><div class="output-body"><ComparisonResult result={localResult} /></div></Panel
    >{/if}
  <div class="step-actions">
    <button class="button" onclick={() => goToStep('run')}>Run another comparison</button><button
      class="button"
      onclick={() => goToStep('input')}>Edit Python</button
    >
  </div>
  <p>
    Want a larger computation? The compiler supports up to six binary choices. <a
      class="text-link"
      href="/optimization/?example=large">Try the 16-choice workload benchmark →</a
    >
  </p>
{/if}

<style>
  .workflow-nav,
  .step-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin: 20px 0;
  }
  .compiler-layout {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 24px;
  }
  .configuration,
  .source-editor,
  .output-body {
    padding: 20px;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0 0 24px;
  }
  legend {
    font-weight: 500;
    margin-bottom: 12px;
  }
  label {
    display: block;
    margin: 8px 0;
    font-size: 14px;
  }
  select,
  textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: 4px;
  }
  textarea {
    font: 13px/1.7 var(--mono);
    resize: vertical;
  }
  .editor-heading,
  .editor-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin: 10px 0;
  }
  .field-note,
  .file-name,
  .character-count {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.7;
  }
  .advanced-body {
    padding: 12px 0;
  }
  h2 {
    font-size: 22px;
    margin: 20px 0;
  }
  h3 {
    font-size: 16px;
  }
  p {
    line-height: 1.7;
  }
  details {
    margin: 16px 0;
  }
  summary {
    cursor: pointer;
  }
  @media (max-width: 1100px) {
    .compiler-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
