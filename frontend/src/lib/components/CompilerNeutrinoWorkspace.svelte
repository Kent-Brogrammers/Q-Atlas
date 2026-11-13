<script lang="ts">
  import { onDestroy } from 'svelte';
  import { api } from '../../api/client.ts';
  import type { CompiledNeutrino, NeutrinoResponse, HardwareJob } from '../../types/index.ts';
  import ExecutionChoice from './ExecutionChoice.svelte';
  import CompilerNeutrinoResult from './CompilerNeutrinoResult.svelte';
  import { downloadJson } from '../studies/model.ts';
  let {
    source,
    compiled,
    onResult,
    onJob
  }: {
    source: string;
    compiled: CompiledNeutrino;
    onResult: (result: NeutrinoResponse) => void;
    onJob: (job: HardwareJob | null) => void;
  } = $props();
  let busy = $state(false),
    error = $state('');
  let result = $state<NeutrinoResponse | null>(null);
  let controller: AbortController | undefined;
  onDestroy(() => controller?.abort());
  async function run() {
    if (busy) return;
    busy = true;
    error = '';
    controller = new AbortController();
    try {
      const measured = await api.benchmarkNeutrinos({ source }, controller.signal);
      controller.signal.throwIfAborted();
      result = measured;
      onResult(measured);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Neutrino comparison failed.';
    } finally {
      busy = false;
    }
  }
</script>

<p>
  {compiled.method}. The source settings are the same normalized model used by the Neutrino Lab.
</p>
<ExecutionChoice experiment="neutrinos" request={compiled.request} {onJob} automatic={false}>
  <button class="button primary" disabled={busy} onclick={run}
    >{busy ? 'Simulating neutrinos…' : 'Run neutrino comparison'}</button
  >
  {#if busy}<button class="button" onclick={() => controller?.abort()}>Stop waiting</button>
    <p role="status">Comparing classical and compiled circuits at every input point…</p>{/if}
  {#if error}<p role="alert">{error}</p>{/if}
  {#if result}<CompilerNeutrinoResult {result} /><button
      class="button"
      onclick={() =>
        downloadJson(
          { source, request: compiled.request, result },
          'compiler-neutrino-comparison.json'
        )}>Download neutrino comparison</button
    >{/if}
</ExecutionChoice>
<details>
  <summary>Inspect generated circuit and experiment settings</summary>
  <pre>{compiled.circuit_diagram}</pre>
  <pre>{JSON.stringify(compiled.request, null, 2)}</pre>
</details>

<style>
  p {
    line-height: 1.7;
  }
  pre {
    overflow: auto;
    font-size: 12px;
  }
</style>
