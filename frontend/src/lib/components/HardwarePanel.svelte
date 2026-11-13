<script lang="ts">
  import { onDestroy, onMount, untrack } from 'svelte';
  import { api, ApiError } from '../../api/client.ts';
  import type {
    HardwareJob,
    HardwareRequest,
    HardwareReadiness,
    CompilerHardwareDevices
  } from '../../types/index.ts';
  import type { Experiment, Requests } from '../studies/model.ts';
  import { downloadJson } from '../studies/model.ts';
  import {
    canStartAnother,
    canSubmit,
    hardwareTask,
    makeRequest,
    pickHardwareJob
  } from '../hardware/requests.ts';
  import HardwareAnalytics from './HardwareAnalytics.svelte';
  import Panel from './Panel.svelte';
  import { loadPhysicalRecording } from '../hardware/recorded.ts';
  let {
    experiment,
    request = null,
    suiteTask = null,
    simple = false,
    onJob
  }: {
    experiment: Experiment | 'suite';
    request?: Requests[Experiment] | null;
    suiteTask?: HardwareRequest['task'] | null;
    simple?: boolean;
    onJob?: (job: HardwareJob | null) => void;
  } = $props();
  let backend = $state('');
  let shots = $state(128);
  let points = $state(3);
  let steps = $state(4);
  let layers = $state(1);
  let devices = $state<CompilerHardwareDevices | null>(null);
  let readiness = $state<HardwareReadiness | null>(null);
  let recordedMode = $state(false);
  let expanded = $state(untrack(() => simple || experiment === 'suite'));
  let readinessError = $state('');
  let job = $state<HardwareJob | null>(null);
  let requestId = $state('');
  let busy = $state(false);
  let error = $state('');
  let autoRefresh = $state(true);
  let alive = true;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let preview = $derived.by(() => {
    try {
      if (!Number.isInteger(shots) || shots < 1 || shots > 128)
        throw new Error('QPU shots must be 1–128.');
      if (experiment === 'suite') return { task: suiteTask, error: '' };
      return {
        task: request ? hardwareTask(experiment, request, shots, points, steps, layers) : null,
        error: ''
      };
    } catch (cause) {
      return {
        task: null,
        error: cause instanceof Error ? cause.message : 'Invalid QPU settings.'
      };
    }
  });
  let storageKey = $derived(`qatlas-all-qpu-${experiment}`);
  onMount(() => {
    void refreshReadiness();
    try {
      requestId = localStorage.getItem(storageKey) ?? '';
    } catch {
      /* Storage can be disabled. */
    }
    if (requestId) void action('refresh');
    else
      void api
        .hardwareJobs(experiment)
        .then((records) => {
          if (alive && !recordedMode && records[0]) {
            job = records[0];
            requestId = records[0].request_id;
          }
        })
        .catch(() => {});
  });
  $effect(() => {
    clearTimeout(timer);
    if (!recordedMode && autoRefresh && job?.job_id && !canStartAnother(job) && !busy)
      timer = setTimeout(() => {
        if (alive) void action('refresh');
      }, 15000);
  });
  $effect(() => {
    onJob?.(job);
  });
  onDestroy(() => {
    alive = false;
    clearTimeout(timer);
  });
  async function refreshReadiness() {
    try {
      const found = await api.hardwareReadiness();
      if (alive) {
        readiness = found;
        readinessError = '';
      }
    } catch {
      if (alive) {
        readiness = null;
        readinessError =
          'Backend readiness is unavailable. Start the local API to submit jobs, or load the recorded physical demo.';
      }
    }
  }
  function loadRecording() {
    if (busy) return;
    try {
      job = loadPhysicalRecording(experiment);
      recordedMode = true;
      error = '';
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Archived evidence could not load.';
    }
  }
  let submissionReady = $derived(
    readiness?.configured &&
      readiness.sdk_installed &&
      (readiness.remaining_reservation_seconds ?? 0) >= 10
  );
  let blockedReason = $derived.by(() => {
    if (busy) return 'An IBM operation is in progress.';
    if (!readiness) return readinessError || 'Checking hardware readiness…';
    if (!readiness.configured || !readiness.sdk_installed) return readiness.message;
    if (!submissionReady)
      return `Local QPU budget has ${readiness.remaining_reservation_seconds ?? 0} seconds available; this job needs a 10-second reservation. Check existing jobs to reconcile completed usage, then refresh readiness.`;
    if (!preview.task) return preview.error || 'Choose valid experiment settings first.';
    if (!canSubmit(job, requestId))
      return 'A previous request still needs status recovery or completion. Use Check QPU job before submitting another.';
    return '';
  });
  async function action(kind: 'devices' | 'submit' | 'refresh' | 'cancel') {
    if (busy) return;
    busy = true;
    error = '';
    try {
      if (kind === 'devices') {
        const found = await api.hardwareDevices();
        if (alive) devices = found;
      } else if (kind === 'submit') {
        if (!submissionReady || !preview.task || !canSubmit(job, requestId)) return;
        const id = crypto.randomUUID();
        // Save before the network call. A lost acknowledgement must retain the same ID.
        localStorage.setItem(storageKey, id);
        requestId = id;
        recordedMode = false;
        job = null;
        const measured = await api.submitHardware(makeRequest(preview.task, id, backend, shots));
        if (alive) {
          job = pickHardwareJob(measured, experiment);
          void refreshReadiness();
        }
      } else if (requestId) {
        const measured =
          kind === 'cancel'
            ? await api.cancelHardwareJob(requestId)
            : await api.hardwareJob(requestId);
        if (alive) {
          job = pickHardwareJob(measured, experiment);
          recordedMode = false;
          void refreshReadiness();
        }
      }
    } catch (cause) {
      if (alive) {
        error =
          cause instanceof Error
            ? cause.message
            : 'Hardware operation failed. Keep the request ID and retry status retrieval.';
        if (
          kind === 'submit' &&
          cause instanceof ApiError &&
          cause.status === 422 &&
          !(cause.body.error.diagnostics ?? []).some((d) => d.code === 'HARDWARE_REQUEST_CONFLICT')
        ) {
          localStorage.removeItem(storageKey);
          requestId = '';
        }
      }
    } finally {
      if (alive) busy = false;
    }
  }
</script>

{#if !simple && experiment !== 'suite'}
  <nav class="experiment-shortcuts" aria-label="Experiment sections">
    <a href="#local-experiment">Local experiment</a>
    <a href="#physical-experiment" onclick={() => (expanded = true)}>Physical QPU</a>
    <a href="#parameter-study">Parameter study</a>
  </nav>
{/if}
<details
  id="physical-experiment"
  class="hardware-disclosure"
  class:simple
  bind:open={expanded}
  ontoggle={() => {
    if (expanded) void refreshReadiness();
  }}
>
  <summary>
    Physical QPU · hardware settings &amp; recorded results
    <span>Use an IBM device or view the saved physical demo.</span>
  </summary>
  <Panel
    title="Run on an IBM quantum computer"
    subtitle="Physical QPU · credentials loaded privately by the backend from .env"
  >
    <div class="hardware-body">
      <p>
        Run the configured {experiment} experiment on a physical IBM device and compare it with its independent
        classical reference. One submission uses a maximum execution-time cap of 10 seconds. The shared
        reservation cap includes compiler jobs.
      </p>
      <details class="advanced-settings">
        <summary>Change hardware settings</summary>
        <fieldset disabled={busy}>
          <div class="settings">
            <label
              >IBM device<select bind:value={backend}
                ><option value="">Automatically choose an accessible least-busy QPU</option
                >{#each devices?.backends ?? [] as name}<option value={name}>{name}</option
                  >{/each}</select
              ></label
            >
            <label
              >QPU shots per circuit<input
                type="number"
                min="1"
                max="128"
                bind:value={shots}
              /></label
            >
            {#if experiment === 'materials' || experiment === 'neutrinos'}<label
                >QPU curve points<input
                  type="number"
                  min={experiment === 'neutrinos' ? 2 : 1}
                  max="5"
                  bind:value={points}
                /></label
              >{/if}
            {#if experiment === 'materials'}<label
                >QPU Trotter steps<input type="number" min="1" max="32" bind:value={steps} /></label
              >{/if}
            {#if experiment === 'compiler' || experiment === 'optimization'}<label
                >QPU QAOA layers<input type="number" min="1" max="2" bind:value={layers} /></label
              >{/if}
          </div>
        </fieldset>
        <p class="note">
          QPU shots and the QPU resolution controls above are separate from local simulator
          settings. Scientific coefficients and the problem instance follow the page's settings.
          Inspect the effective request before submitting.
        </p>
        {#if preview.error}<p role="alert">{preview.error}</p>{/if}
        {#if preview.task}<details>
            <summary>Effective hardware request</summary>
            <pre>{JSON.stringify(
                {
                  task: preview.task,
                  shots,
                  max_execution_seconds: 10,
                  backend_name: backend || null
                },
                null,
                2
              )}</pre>
          </details>{/if}
      </details>
      <div class="actions">
        <button
          class="button primary"
          disabled={!!blockedReason}
          title={blockedReason || 'Submit this experiment to an IBM quantum computer'}
          onclick={() => action('submit')}>{busy ? 'Working with IBM…' : 'Run on IBM QPU'}</button
        >
        <button class="button" disabled={busy} onclick={loadRecording}>View recorded example</button
        >
      </div>
      <details>
        <summary>Connection &amp; job tools</summary>
        <div class="actions">
          <button class="button" disabled={busy} onclick={() => action('devices')}
            >List available devices</button
          >
          <button class="button" disabled={busy} onclick={refreshReadiness}
            >Refresh readiness</button
          >
        </div>
      </details>
      {#if blockedReason}<p class="run-blocked" role="status">
          <strong>Run unavailable:</strong>
          {blockedReason}
        </p>{/if}
      {#if readiness}
        <p class="note" role="status">
          {readiness.message}
          {#if readiness.reserved_seconds != null}Local reservation: {readiness.reserved_seconds} / {readiness.budget_seconds}
            seconds (recorded usage + outstanding reservations). This is not IBM's measured remaining
            balance.{/if}
        </p>
      {:else}<p class="note" role="status">
          {readinessError || 'Checking local hardware configuration and reservation…'}
        </p>{/if}
      {#if recordedMode}<p class="recording-banner" role="status">
          <strong>Previously measured physical QPU demo — not a new run.</strong> Loaded from the
          archived evidence without an API request. Original request created: {job?.created_at_utc}.
        </p>{/if}
      {#if devices}<p class="note">
          Shared local reservation: {devices.reserved_seconds} / {devices.budget_seconds} seconds. This
          is a conservative local cap, not the provider's remaining balance.
        </p>{/if}
      {#if error}<p role="alert">
          {error}
          {#if requestId}Keep request ID {requestId} and check status before another submission.{/if}
        </p>{/if}
      {#if requestId}<p class="note">Request ID: {requestId}</p>
        <button class="button" disabled={busy} onclick={() => action('refresh')}
          >Check QPU job</button
        >{/if}
      {#if job}
        <p role="status">
          <strong>{job.status}</strong> · Device: {job.backend_name ?? 'Selecting'} · Provider job: {job.job_id ??
            'Not acknowledged yet'}
        </p>
        <p class="note">
          Recorded at {job.created_at_utc}. Last saved update: {job.updated_at_utc}.
        </p>
        <p>{job.message}</p>
        <label class="poll"
          ><input type="checkbox" bind:checked={autoRefresh} />Refresh active job status every 15
          seconds</label
        >
        {#if job.job_id}<a
            href={`https://quantum.cloud.ibm.com/workloads/${encodeURIComponent(job.job_id)}`}
            target="_blank"
            rel="noreferrer">Open IBM workload</a
          >{/if}
        <div class="actions">
          <button
            class="button"
            onclick={() =>
              downloadJson(
                job,
                `q-atlas-${experiment}-${recordedMode ? 'recorded-' : ''}physical-qpu.json`
              )}>Download physical QPU evidence</button
          >{#if job.job_id && !canStartAnother(job)}<button
              class="button"
              disabled={busy}
              onclick={() => action('cancel')}>Cancel QPU job</button
            >{/if}
        </div>
        <p class="note">
          This stored job retains its original inputs even when page settings change. Queued,
          running, failed and unknown submissions are not reported as measurements.
        </p>
        {#if job.measurement_complete}
          <HardwareAnalytics {job} />
          {#each job.children ?? [] as child}<details open>
              <summary>{child.task.kind} · physical QPU comparison</summary><HardwareAnalytics
                job={child}
              />
            </details>{/each}
        {/if}
      {/if}
    </div>
  </Panel>
</details>
{#if !simple && experiment !== 'suite'}
  <h2 id="local-experiment" tabindex="-1">Local experiment</h2>
{/if}

<style>
  .simple > summary {
    display: none;
  }
  details.advanced-settings {
    margin-bottom: 18px;
  }
  .experiment-shortcuts {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 0 0 16px;
  }
  .experiment-shortcuts a {
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--blue);
    background: var(--surface);
    font-size: 14px;
  }
  .hardware-disclosure {
    margin-bottom: 24px;
  }
  .hardware-disclosure > summary {
    cursor: pointer;
    padding: 16px;
    background: var(--surface-raised);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-weight: 500;
  }
  summary span {
    display: block;
    margin-top: 5px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 400;
  }
  h2 {
    font-size: 18px;
    font-weight: 500;
    margin: 20px 0 12px;
  }
  .hardware-body {
    padding: 0 22px 22px;
  }
  p {
    font-size: 13px;
    line-height: 1.7;
  }
  .note {
    color: var(--muted);
    font-size: 12px;
  }
  .recording-banner {
    border: 1px solid var(--border);
    padding: 12px;
    background: var(--surface-raised);
  }
  .settings {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 15px 0;
  }
  label {
    display: grid;
    gap: 8px;
    font-size: 12px;
    color: var(--muted);
  }
  input,
  select {
    min-width: 0;
    width: 100%;
    padding: 9px;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 14px 0;
  }
  .poll {
    display: flex;
    align-items: center;
    margin: 14px 0;
  }
  .poll input {
    width: auto;
  }
  pre {
    overflow: auto;
    max-height: 300px;
    font-size: 12px;
  }
</style>
