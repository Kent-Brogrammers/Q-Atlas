<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../../api/client.ts';
  import type { HardwareRequest } from '../../types/index.ts';
  import HardwarePanel from '#lib/components/HardwarePanel.svelte';
  let preset = $state<HardwareRequest | null>(null);
  let error = $state('');
  onMount(() => {
    void api
      .hardwareDemo()
      .then((value) => {
        preset = value;
      })
      .catch((cause) => {
        error = cause instanceof Error ? cause.message : 'Start the backend to load the preset.';
      });
  });
</script>

<svelte:head><title>Physical QPU Analytics · Q-Atlas</title></svelte:head>
<header class="page-heading">
  <div>
    <h1>Physical QPU Analytics</h1>
    <p>Recorded neutrino and compiler measurements from a physical IBM quantum computer.</p>
  </div>
</header>
<p class="intro">
  Neutrino Lab and Python Compiler are featured below. The original IBM job also measured
  Optimization, Materials and Grover Search. All five experiments retain their measurements and
  references. Device usage and wall time describe the shared job.
</p>
{#if error}<p role="alert">{error}</p>{/if}
<HardwarePanel experiment="suite" suiteTask={preset?.task ?? null} />

<style>
  .intro {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.8;
    max-width: 900px;
    margin-bottom: 25px;
  }
</style>
