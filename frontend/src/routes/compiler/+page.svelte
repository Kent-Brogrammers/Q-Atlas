<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import Icon from '#lib/components/Icon.svelte';
  import Panel from '#lib/components/Panel.svelte';
  import Metric from '#lib/components/Metric.svelte';
  import { api, ApiError } from '../../api/client.ts';
  import type {
    CompilerAnalyzeResult,
    GeneratedPythonArtifact,
    CompilerBenchmarkPlan,
    CompilerHardwareJob,
    CompilerHardwareDevices
  } from '../../types/index.ts';
  import {
    DEFAULT_SCRIPT,
    MAX_SOURCE_LENGTH,
    readObjectiveFile,
    generatedFilename,
    formatOptionalMs,
    formatAngle
  } from '../../compiler/source.ts';
  import { PROGRAM_EXAMPLES } from '../../compiler/examples.ts';

  const steps = [
    { id: 'input', label: 'Python input', title: 'Start with your Python' },
    { id: 'compiled', label: 'Compiled code', title: 'Review your compiled code' },
    { id: 'test', label: 'Test', title: 'Prepare your comparison' },
    { id: 'results', label: 'Results & analytics', title: 'Review your results and analytics' }
  ] as const;
  type Step = (typeof steps)[number]['id'];
  const communicationFields = [
    {
      key: 'submission_ms',
      label: 'Send / submit',
      note: 'Sampler submission to provider job acknowledgement'
    },
    {
      key: 'result_retrieval_ms',
      label: 'Receive results',
      note: 'Ready-result download'
    },
    {
      key: 'queue_ms',
      label: 'Provider queue',
      note: 'Remote waiting time, reported by the provider'
    },
    {
      key: 'remote_processing_ms',
      label: 'Remote processing',
      note: 'Provider-reported processing · not QPU quota usage'
    },
    {
      key: 'round_trip_ms',
      label: 'Provider round trip',
      note: 'Submit through received results, including waits and overhead'
    }
  ] as const;
  let step = $state<Step>('input');
  let stageHeading = $state<HTMLHeadingElement>();

  let source = $state(DEFAULT_SCRIPT);
  let fileName = $state('selection.py');
  let example = $state('default');
  let layers = $state(1);
  let analysis = $state<CompilerAnalyzeResult>();
  let artifact = $state<GeneratedPythonArtifact>();
  let plan = $state<CompilerBenchmarkPlan>();
  let hardwareDevices = $state<CompilerHardwareDevices>();
  let hardwareBackend = $state('');
  let hardwareConfirmed = $state(false);
  let hardwareBusy = $state(false);
  let hardwareJob = $state<CompilerHardwareJob>();
  let hardwareRequestId = $state('');
  let hardwareUrl = $state('');
  let error = $state('');
  let loading = $state<'generate' | 'plan' | null>(null);
  let reading = $state(false);
  let generatedUrl = $state('');
  let planUrl = $state('');
  let editor = $state<HTMLTextAreaElement>();
  let revision = 0;
  let readSequence = 0;
  let active = true;
  const busy = $derived(loading !== null || reading || hardwareBusy);
  const stepIndex = $derived(steps.findIndex((item) => item.id === step));
  const currentHardwareJob = $derived(
    hardwareJob?.problem_id === plan?.problem_id ? hardwareJob : undefined
  );
  function communicationValue(key: (typeof communicationFields)[number]['key']) {
    if (currentHardwareJob) {
      if (key === 'submission_ms') return currentHardwareJob.submission_ms;
      if (key === 'result_retrieval_ms') return currentHardwareJob.measurement?.retrieval_ms;
      return null;
    }
    return plan?.communication_timing?.[key];
  }
  onMount(() => {
    try {
      hardwareRequestId = localStorage.getItem('qatlas-compiler-qpu-request') ?? '';
    } catch {
      /* Storage may be unavailable. */
    }
  });
  $effect(() => {
    hardwareUrl = '';
    if (!hardwareJob) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(hardwareJob, null, 2)], { type: 'application/json' })
    );
    hardwareUrl = url;
    return () => URL.revokeObjectURL(url);
  });
  async function hardwareAction(action: 'devices' | 'submit' | 'refresh' | 'cancel') {
    if (busy) return;
    if (
      action === 'submit' &&
      (!hardwareConfirmed || !hardwareBackend || layers !== 1 || !artifact)
    )
      return;
    hardwareBusy = true;
    error = '';
    try {
      if (action === 'devices') {
        const devices = await api.compilerHardwareDevices();
        if (active) hardwareDevices = devices;
      } else if (action === 'submit') {
        const prepared =
          plan ??
          (await api.prepareCompilerBenchmark({
            source,
            config: { p: 1, shots: 128, max_iterations: 20, timeout_seconds: 30 }
          }));
        if (!active) return;
        plan = prepared;
        if (!hardwareRequestId) {
          const requestId = crypto.randomUUID();
          localStorage.setItem('qatlas-compiler-qpu-request', requestId);
          hardwareRequestId = requestId;
        }
        const job = await api.submitCompilerHardware({
          source,
          backend_name: hardwareBackend,
          request_id: hardwareRequestId,
          confirmed: true,
          shots: 128,
          max_execution_seconds: 10
        });
        if (active) {
          hardwareJob = job;
          hardwareConfirmed = false;
          await goToStep('results');
        }
      } else {
        if (!hardwareRequestId) return;
        const job =
          action === 'cancel'
            ? await api.cancelCompilerHardwareJob(hardwareRequestId)
            : await api.compilerHardwareJob(hardwareRequestId);
        if (active) hardwareJob = job;
      }
    } catch (caught) {
      if (active)
        error =
          caught instanceof Error
            ? caught.message
            : 'Hardware request failed. Recover the recorded request before submitting again.';
    } finally {
      if (active) hardwareBusy = false;
    }
  }
  function newHardwareTest() {
    if (
      busy ||
      !hardwareJob ||
      !['DONE', 'CANCELLED', 'ERROR', 'FAILED_BEFORE_SUBMISSION'].includes(hardwareJob.status)
    )
      return;
    localStorage.removeItem('qatlas-compiler-qpu-request');
    hardwareRequestId = '';
    hardwareJob = undefined;
    hardwareConfirmed = false;
  }

  function canVisit(target: Step) {
    return target === 'input' || (target === 'results' ? !!plan : !!artifact);
  }
  async function goToStep(target: Step) {
    if (!canVisit(target)) return;
    step = target;
    await tick();
    if (active && step === target) {
      stageHeading?.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }

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
    hardwareConfirmed = false;
    step = 'input';
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
          if (artifact) await goToStep('compiled');
        }
      } else {
        const result = await api.prepareCompilerBenchmark({ source, config: { p: layers } });
        if (active && revision === currentRevision) {
          plan = result;
          await goToStep('results');
        }
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
    The Test step can submit one confirmed IBM QPU sampling job.</span
  >
</p>

{#if hardwareRequestId}
  <Panel title="IBM QPU job tracker" subtitle="Hardware sampling after local QAOA angle training">
    <div class="output-body">
      <p>
        Request {hardwareRequestId} · {hardwareJob?.status ?? 'Recover recorded request status'}
      </p>
      {#if hardwareJob}<p>
          Device: {hardwareJob.backend_name} · Provider job: {hardwareJob.job_id ??
            'Not acknowledged yet'} · Problem: {hardwareJob.problem_id}
        </p>{/if}
      {#if hardwareJob?.status === 'SUBMISSION_UNKNOWN'}<p role="alert">
          Submission acknowledgement was lost. Do not create another job. Recover the tagged request
          in IBM's dashboard.
        </p>{/if}
      {#if hardwareJob?.measurement}
        <p role="status">
          Physical QPU result received · simulated: false. Bitstring {hardwareJob.measurement
            .best_bitstring}, canonical objective {hardwareJob.measurement.objective}, optimality
          gap {hardwareJob.measurement.optimality_gap}.
        </p>
        <p>
          Actual shots: {hardwareJob.measurement.shots} · Provider-reported QPU usage: {hardwareJob
            .measurement.quantum_seconds == null
            ? 'Not available'
            : hardwareJob.measurement.quantum_seconds + ' seconds'}
        </p>
        <p>
          Send: {formatOptionalMs(hardwareJob.submission_ms)} · Receive: {formatOptionalMs(
            hardwareJob.measurement.retrieval_ms
          )}
        </p>
      {/if}
      <div class="comparison-actions">
        <button class="button" disabled={busy} onclick={() => hardwareAction('refresh')}
          >Check hardware job</button
        >
        {#if hardwareJob?.job_id && !hardwareJob.measurement}<button
            class="button"
            disabled={busy}
            onclick={() => hardwareAction('cancel')}>Cancel hardware job</button
          >{/if}
        {#if hardwareUrl}<a class="button" href={hardwareUrl} download="q_atlas_qpu_job.json"
            >Download QPU record</a
          >{/if}
        {#if hardwareJob && ['DONE', 'CANCELLED', 'ERROR', 'FAILED_BEFORE_SUBMISSION'].includes(hardwareJob.status)}<button
            class="button"
            disabled={busy}
            onclick={newHardwareTest}>Start a new hardware test</button
          >{/if}
      </div>
      <p class="field-note">
        This tracker retains the job's own problem ID even if you edit the source. Checking or
        recovering never submits another job.
      </p>
    </div>
  </Panel>
{/if}

<nav class="workflow-nav" aria-label="Compiler workflow">
  <ol>
    {#each steps as item, index}
      <li>
        <button
          class:current={step === item.id}
          class:complete={index < stepIndex}
          aria-current={step === item.id ? 'step' : undefined}
          disabled={busy || !canVisit(item.id)}
          onclick={() => goToStep(item.id)}
        >
          <span class="step-number">{index + 1}</span><span>{item.label}</span>
        </button>
      </li>
    {/each}
  </ol>
</nav>

<section class="workflow-stage" aria-labelledby="compiler-stage-title" aria-busy={busy}>
  <header class="stage-heading">
    <p class="eyebrow">Step {stepIndex + 1} of {steps.length}</p>
    <h2 id="compiler-stage-title" tabindex="-1" bind:this={stageHeading}>
      {steps[stepIndex].title}
    </h2>
  </header>

  <div
    class="request-status"
    class:has-status={reading || loading === 'plan' || !!error}
    aria-live="polite"
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
                  The default is one layer. If you have an existing zero-argument circuit factory,
                  mark it with <code>@qatlas.circuit</code> to replace it. Otherwise the compiler adds
                  the generated builder automatically.
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
              <span class="character-count"
                >{source.length.toLocaleString()} / 20,000 characters</span
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
                Keep the ordinary script around the marked function. The marked region currently
                needs bounded binary arithmetic.
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
            <button class="button" disabled={busy} onclick={() => goToStep('compiled')}
              >View compiled code<Icon name="arrow" size={15} /></button
            >
          </div>
        {/if}
      </div>
    </div>
  {:else if step === 'compiled' && artifact}
    <Panel title="Compiled Python" subtitle="Generated and verified · not executed">
      {#snippet toolbar()}
        {#if generatedUrl}<a
            class="button primary"
            href={generatedUrl}
            download={generatedFilename(fileName)}>Download .py<Icon name="download" size={15} /></a
          >{/if}
      {/snippet}
      <div class="output-body">
        <p>
          Your program and function names are preserved.
          {#if artifact.replaced_function}The marked {artifact.replaced_function}() factory was
            replaced.
          {:else}The generated builder was added automatically.{/if}
        </p>
        <p class="field-note">Review the generated code, then continue to test preparation.</p>
      </div>
      <div class="preview-body">
        <label for="generated-python">Generated Python source</label>
        <textarea
          id="generated-python"
          readonly
          value={artifact.source}
          rows="20"
          spellcheck="false"
        ></textarea>
      </div>
    </Panel>
    <div class="step-actions">
      <button class="button" disabled={busy} onclick={() => goToStep('input')}
        >Back to Python</button
      >
      <button class="button primary" disabled={busy} onclick={() => goToStep('test')}
        >Continue to test<Icon name="arrow" size={15} /></button
      >
    </div>
  {:else if step === 'test' && artifact}
    <Panel title="Test preparation" subtitle="Compare solvers on the same verified objective">
      <div class="output-body">
        <p>
          Prepare a comparison for your marked objective. Your surrounding Python application is not
          run or timed.
        </p>
        <dl class="test-summary">
          <div>
            <dt>Source</dt>
            <dd>{fileName}</dd>
          </div>
          <div>
            <dt>Comparison</dt>
            <dd>Exact classical optimum and QPU samples</dd>
          </div>
          <div>
            <dt>Circuit layers</dt>
            <dd>{layers}</dd>
          </div>
          <div>
            <dt>Execution</dt>
            <dd>IBM QPU · confirmed submission only</dd>
          </div>
        </dl>
      </div>
      <div class="output-placeholder">
        <Icon name="info" size={24} />
        <div>
          <h3>Submit one physical quantum job</h3>
          <p>
            Angles are trained locally, then one bound circuit is sampled on your selected IBM QPU.
            Initial tests allow three inputs, one layer, 128 shots and a 10-second QPU cap. Check
            your actual remaining IBM allowance before submitting.
          </p>
          <div class="comparison-actions">
            <button class="button" disabled={busy} onclick={() => hardwareAction('devices')}
              >Load IBM devices</button
            >
          </div>
          {#if hardwareDevices}
            <p class="field-note">
              Compiler reservation: {hardwareDevices.reserved_seconds} / {hardwareDevices.budget_seconds}
              seconds. This is not provider remaining quota.
            </p>
            <label for="hardware-backend">IBM device</label>
            <select id="hardware-backend" bind:value={hardwareBackend} disabled={busy}>
              <option value="">Choose a device</option
              >{#each hardwareDevices.backends as name}<option value={name}>{name}</option>{/each}
            </select>
            <label class="hardware-confirm"
              ><input type="checkbox" bind:checked={hardwareConfirmed} disabled={busy} />I checked
              IBM's remaining allowance and authorize one job with a 10-second QPU cap.</label
            >
            <button
              class="button primary"
              disabled={busy ||
                !hardwareConfirmed ||
                !hardwareBackend ||
                layers !== 1 ||
                (analysis?.qubo?.num_variables ?? 99) > 3}
              onclick={() => hardwareAction('submit')}
              >{hardwareBusy ? 'Working…' : 'Submit one IBM QPU job'}</button
            >
            {#if layers !== 1 || (analysis?.qubo?.num_variables ?? 99) > 3}<p class="field-note">
                Use one layer and at most three binary inputs for this initial test.
              </p>{/if}
          {/if}
        </div>
      </div>
    </Panel>
    <div class="step-actions">
      <button class="button" disabled={busy} onclick={() => goToStep('compiled')}
        >Back to compiled code</button
      >
      <button
        class="button primary"
        disabled={busy}
        onclick={() => (plan ? goToStep('results') : run('plan'))}
      >
        {loading === 'plan'
          ? 'Preparing…'
          : plan
            ? 'View results & analytics'
            : 'Prepare test plan'}<Icon name="arrow" size={15} />
      </button>
    </div>
  {:else if step === 'results' && plan && analysis?.status === 'supported'}
    <div class="analytics-workspace">
      <Panel
        title="Test status"
        subtitle={currentHardwareJob
          ? `IBM QPU · ${currentHardwareJob.status}`
          : 'Comparison prepared · not executed'}
      >
        {#snippet toolbar()}
          {#if planUrl}<a class="button" href={planUrl} download="q_atlas_benchmark_plan.json"
              >Download test plan<Icon name="download" size={15} /></a
            >{/if}
        {/snippet}
        <div class="output-body">
          <p role="status">
            {#if currentHardwareJob}
              The hardware request is recorded above. Check its status manually to retrieve results.
              QAOA angles are trained locally; final sampling uses the selected physical QPU. Your
              surrounding Python application is not executed.
            {:else}
              Your comparison plan is ready. No script or solver has been executed, so measured
              performance results are not available yet.
            {/if}
          </p>
          <dl class="test-summary">
            <div>
              <dt>{currentHardwareJob ? 'Hardware' : 'Planned'} layers / shots / seed</dt>
              <dd>
                {currentHardwareJob?.local_training_config.p ?? plan.config.p} / {currentHardwareJob?.shots ??
                  plan.config.shots} / {currentHardwareJob?.local_training_config.seed ??
                  plan.config.seed}
              </dd>
            </div>
            <div>
              <dt>Problem ID</dt>
              <dd>{plan.problem_id}</dd>
            </div>
          </dl>
        </div>
      </Panel>
      <section aria-labelledby="compilation-analytics-title">
        <h3 id="compilation-analytics-title">Compilation analytics</h3>
        <div class="analytics-grid">
          <Metric
            label="Binary inputs"
            value={plan.qubo.num_variables}
            note="Verified objective width"
          />
          <Metric
            label="Circuit layers"
            value={plan.circuit.p}
            note="Generated plan · not executed"
          />
          <Metric
            label="Logical depth"
            value={plan.circuit.logical_depth}
            note="Before transpilation · not measured"
          />
        </div>
      </section>
      <section aria-labelledby="performance-title">
        <h3 id="performance-title">Measured performance</h3>
        <div class="analytics-grid performance-grid">
          <Metric
            label="Classical runtime"
            value={currentHardwareJob?.classical
              ? formatOptionalMs(currentHardwareJob.classical.elapsed_ms)
              : 'Not run'}
            note="Exact enumeration of the same canonical QUBO"
          />
          <Metric
            label="Local angle training"
            value={currentHardwareJob?.local_training_ms != null
              ? formatOptionalMs(currentHardwareJob.local_training_ms)
              : 'Not run'}
            note="Local simulator · before physical sampling"
          />
          <Metric
            label="QPU usage"
            value={currentHardwareJob?.measurement?.quantum_seconds != null
              ? `${currentHardwareJob.measurement.quantum_seconds} s`
              : 'Not reported'}
            note="Provider usage · excludes local training and queue"
          />
          <Metric
            label="Optimality gap"
            value={currentHardwareJob?.measurement?.optimality_gap ?? 'Not measured'}
            note="Sampled canonical objective minus exact minimum"
          />
        </div>
        <p class="timing-note">
          The timings cover different work and do not establish a speedup. This is local angle
          training followed by physical QPU sampling, rather than optimization on the QPU.
        </p>
      </section>
      <section aria-labelledby="communication-title">
        <h3 id="communication-title">Quantum communication timing</h3>
        <p class="timing-note">
          {currentHardwareJob
            ? 'Submission and ready-result retrieval are measured when available. Queue, remote processing and full round trip remain unmeasured.'
            : 'These placeholders are included in your downloaded test plan. Submit a hardware job to record submission and retrieval timings.'}
        </p>
        <div class="analytics-grid">
          {#each communicationFields as field}
            <Metric
              label={field.label}
              value={formatOptionalMs(communicationValue(field.key))}
              note={field.note}
            />
          {/each}
        </div>
        <p class="timing-note">
          Round-trip time already includes sending, remote waits and processing, and receiving. Do
          not add those components to it again. Unknown timing stays unmeasured, not zero.
        </p>
      </section>
      <details class="panel conversion-details">
        <summary>Objective & circuit details</summary>
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

        <details class="result-disclosure">
          <summary>Raw analysis JSON</summary>
          <pre class="code-block">{JSON.stringify(analysis, null, 2)}</pre>
        </details>
      </details>
      <details class="panel conversion-details">
        <summary>Execution readiness</summary>
        <div class="detail-section">
          {#if currentHardwareJob}
            <p>
              Recorded device: {currentHardwareJob.backend_name}. Maximum QPU usage: {currentHardwareJob.max_execution_seconds}
              seconds. The plan JSON remains a nonexecuting artifact; download the QPU record above for
              measured results.
            </p>
          {:else}
            <ul class="blockers">
              {#each plan.blockers as blocker}<li>{blocker}</li>{/each}
            </ul>
          {/if}
        </div>
      </details>
    </div>
    <div class="step-actions">
      <button class="button" disabled={busy} onclick={() => goToStep('test')}>Back to test</button>
      <button class="button" disabled={busy} onclick={() => goToStep('input')}
        >Edit Python<Icon name="code" size={15} /></button
      >
    </div>
  {/if}
</section>

<style>
  .workflow-nav ol {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    list-style: none;
    padding: 0;
    margin: 0 0 28px;
  }
  .workflow-nav button {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    min-height: 54px;
    padding: 12px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--surface);
    color: var(--muted);
    font-size: 13px;
    text-align: left;
  }
  .workflow-nav button.current {
    border-color: var(--accent, var(--blue));
    color: var(--accent, var(--blue));
    background: var(--surface-raised);
  }
  .workflow-nav button.complete {
    color: var(--text);
  }
  .step-number {
    display: grid;
    place-items: center;
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 12px var(--mono);
  }
  .stage-heading {
    margin-bottom: 20px;
  }
  .stage-heading h2 {
    margin: 6px 0 0;
    font-size: 22px;
    font-weight: 400;
    scroll-margin-top: 20px;
  }
  .stage-heading h2:focus {
    outline: none;
  }
  .step-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 12px;
    margin-top: 20px;
  }
  .workflow-stage > .request-status.has-status {
    margin-bottom: 20px;
  }
  .analytics-workspace {
    display: grid;
    gap: 20px;
    min-width: 0;
  }
  .analytics-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }
  .timing-note {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.7;
    margin: 10px 0 16px;
  }
  .test-summary {
    margin: 16px 0 0;
  }
  .test-summary div {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding: 12px 0;
    border-top: 1px solid var(--border);
    font-size: 13px;
  }
  dt {
    color: var(--muted);
  }
  dd {
    margin: 0;
    text-align: right;
    overflow-wrap: anywhere;
    min-width: 0;
  }
  .availability {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 14px 16px;
    margin: 0 0 24px;
    border-left: 3px solid var(--blue);
    background: var(--surface-raised);
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
    color: var(--muted);
  }
  .hardware-confirm {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    line-height: 1.6;
    margin: 14px 0;
  }
  .output-body p {
    overflow-wrap: anywhere;
  }
  select {
    display: block;
    width: 100%;
    min-height: 40px;
    min-width: 0;
    padding: 9px 10px;
    margin-bottom: 14px;
    background: var(--surface-raised);
    border: 1px solid var(--border);
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
    background: var(--surface-raised);
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
    color: var(--text);
    font: 12px/1.85 var(--mono);
    resize: vertical;
    background: var(--surface-raised);
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
    border-left-color: var(--accent, var(--blue));
    background: var(--surface-raised);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .error-notice :global(svg) {
    color: var(--accent, var(--blue));
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
    background: var(--surface-raised);
    color: var(--muted);
  }
  td {
    font-family: var(--mono);
  }
  .comparison-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 16px;
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
    .workflow-nav ol {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .analytics-grid {
      grid-template-columns: 1fr;
    }
    .step-actions > .button {
      width: 100%;
    }
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
