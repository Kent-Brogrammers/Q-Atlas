<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { api, ApiError } from '../../api/client.ts';
  import type { HardwareJob, HardwareRequest, CompilerHardwareDevices } from '../../types/index.ts';
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
  let {
    experiment,
    request = null,
    suiteTask = null
  }: {
    experiment: Experiment | 'suite';
    request?: Requests[Experiment] | null;
    suiteTask?: HardwareRequest['task'] | null;
  } = $props();
  let backend = $state('');
  let shots = $state(128);
  let points = $state(3);
  let steps = $state(4);
  let layers = $state(1);
  let devices = $state<CompilerHardwareDevices | null>(null);
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
          if (alive && records[0]) {
            job = records[0];
            requestId = records[0].request_id;
          }
        })
        .catch(() => {});
  });
  $effect(() => {
    clearTimeout(timer);
    if (autoRefresh && job?.job_id && !canStartAnother(job) && !busy)
      timer = setTimeout(() => {
        if (alive) void action('refresh');
      }, 15000);
  });
  onDestroy(() => {
    alive = false;
    clearTimeout(timer);
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
        if (!preview.task || !canSubmit(job, requestId)) return;
        const id = crypto.randomUUID();
        // Save before the network call. A lost acknowledgement must retain the same ID.
        localStorage.setItem(storageKey, id);
        requestId = id;
        job = null;
        const measured = await api.submitHardware(makeRequest(preview.task, id, backend, shots));
        if (alive) job = pickHardwareJob(measured, experiment);
      } else if (requestId) {
        const measured =
          kind === 'cancel'
            ? await api.cancelHardwareJob(requestId)
            : await api.hardwareJob(requestId);
        if (alive) job = pickHardwareJob(measured, experiment);
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
          >QPU shots per circuit<input type="number" min="1" max="128" bind:value={shots} /></label
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
      QPU shots and the QPU resolution controls above are separate from local simulator settings.
      Scientific coefficients and the problem instance follow the page's settings. Inspect the
      effective request before submitting.
    </p>
    {#if preview.error}<p role="alert">{preview.error}</p>{/if}
    {#if preview.task}<details>
        <summary>Effective hardware request</summary>
        <pre>{JSON.stringify(preview.task, null, 2)}</pre>
      </details>{/if}
    <div class="actions">
      <button
        class="button primary"
        disabled={busy || !preview.task || !canSubmit(job, requestId)}
        onclick={() => action('submit')}>{busy ? 'Working with IBM…' : 'Run on IBM QPU'}</button
      ><button class="button" disabled={busy} onclick={() => action('devices')}
        >List available devices</button
      >
    </div>
    {#if devices}<p class="note">
        Shared local reservation: {devices.reserved_seconds} / {devices.budget_seconds} seconds. This
        is a conservative local cap, not the provider's remaining balance.
      </p>{/if}
    {#if error}<p role="alert">
        {error}
        {#if requestId}Keep request ID {requestId} and check status before another submission.{/if}
      </p>{/if}
    {#if requestId}<p class="note">Request ID: {requestId}</p>
      <button class="button" disabled={busy} onclick={() => action('refresh')}>Check QPU job</button
      >{/if}
    {#if job}
      <p role="status">
        <strong>{job.status}</strong> · Device: {job.backend_name ?? 'Selecting'} · Provider job: {job.job_id ??
          'Not acknowledged yet'}
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
          onclick={() => downloadJson(job, `q-atlas-${experiment}-physical-qpu.json`)}
          >Download physical QPU evidence</button
        >{#if job.job_id && !canStartAnother(job)}<button
            class="button"
            disabled={busy}
            onclick={() => action('cancel')}>Cancel QPU job</button
          >{/if}
      </div>
      <p class="note">
        This stored job retains its original inputs even when page settings change. Queued, running,
        failed and unknown submissions are not reported as measurements.
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

<style>
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
