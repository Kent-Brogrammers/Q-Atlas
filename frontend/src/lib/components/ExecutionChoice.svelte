<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HardwareJob, HardwareRequest } from '../../types/index.ts';
  import type { Experiment, Requests } from '../studies/model.ts';
  import HardwarePanel from './HardwarePanel.svelte';
  let {
    experiment,
    request,
    children,
    onJob
  }: {
    experiment: Experiment;
    request: Requests[Experiment] | null;
    children: Snippet;
    onJob?: (job: HardwareJob | null) => void;
  } = $props();
  let mode = $state('local');
</script>

<div class="execution-choice">
  <label
    >Where should it run?
    <select bind:value={mode}>
      <option value="local">On this computer · simulator</option>
      <option value="qpu">On an IBM quantum computer · physical QPU</option>
    </select>
  </label>
  <p>
    {mode === 'local'
      ? 'Ready to go. Run the example below, then read the result.'
      : 'Uses your IBM account. Results appear here when the job finishes.'}
  </p>
</div>
<div hidden={mode !== 'local'}>{@render children()}</div>
<div hidden={mode !== 'qpu'}><HardwarePanel {experiment} {request} {onJob} simple /></div>

<style>
  .execution-choice {
    padding: 20px;
    margin: 16px 0 24px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
  }
  label {
    display: grid;
    gap: 10px;
    font-weight: 500;
  }
  select {
    max-width: 540px;
    width: 100%;
    padding: 12px;
    background: var(--surface-raised);
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  p {
    font-size: 14px;
    color: var(--muted);
    margin: 10px 0 0;
  }
</style>
