<script lang="ts">
  import '../app.css';
  import '@fontsource/ibm-plex-sans/latin-400.css';
  import '@fontsource/ibm-plex-sans/latin-500.css';
  import '@fontsource/ibm-plex-sans/latin-600.css';
  import '@fontsource/ibm-plex-mono/latin-400.css';
  import { page } from '$app/state';
  import { fly } from 'svelte/transition';
  import { prefersReducedMotion } from 'svelte/motion';
  import type { Snippet } from 'svelte';
  import { experiments } from '#lib/data/experiments.ts';
  import Icon from '#lib/components/Icon.svelte';
  import Logo from '#lib/components/Logo.svelte';

  let { children }: { children: Snippet } = $props();
  let methodology: HTMLDialogElement;
  let active = $derived(experiments.find((item) => page.url.pathname.startsWith(`/${item.id}`)));
</script>

<svelte:head>
  <meta
    name="description"
    content="Q-Atlas: a scientific workspace for exploring quantum computing through fair, reproducible comparisons."
  />
</svelte:head>

<a class="skip-link" href="#main-content">Skip to workspace</a>
<div class="app-shell">
  <aside class="sidebar" aria-label="Workspace navigation">
    <a class="brand" href="/" aria-label="Q-Atlas overview"
      ><Logo /><span>Q<span class="brand-dash">—</span>Atlas<span class="brand-dot">.</span></span
      ></a
    >
    <div class="workspace-label">
      <span class="status-dot"></span><span>Research workspace</span><span class="workspace-short"
        >QA</span
      >
    </div>
    <p class="nav-heading">EXPERIMENTS</p>
    <nav>
      <a
        class:active={!active}
        href="/"
        aria-current={!active ? 'page' : undefined}
        title="Overview"
        ><Icon name="home" /><span>Overview</span><span class="mobile-nav-label">Overview</span
        ><span class="nav-index">00</span></a
      >
      {#each experiments as item}
        <a
          class:active={active?.id === item.id}
          href="/{item.id}/"
          aria-current={active?.id === item.id ? 'page' : undefined}
          title={item.title}
          ><Icon name={item.icon} /><span>{item.title}</span><span class="mobile-nav-label"
            >{item.short}</span
          ><span class="nav-index">{item.number}</span></a
        >
      {/each}
    </nav>
    <div class="sidebar-bottom">
      <button
        class="methodology-link"
        onclick={() => methodology.showModal()}
        title="Benchmark methodology"
        ><Icon name="book" size={18} /><span>Methodology</span><Icon
          name="northeast"
          size={14}
        /></button
      >
      <div class="sidebar-signature">
        <div class="signature-mark"><Icon name="circuit" size={21} /></div>
        <p>Built for discovery.<br /><span>Powered by curiosity.</span></p>
      </div>
      <p class="sidebar-version">FALL FEST 2026 <span>v0.1</span></p>
    </div>
  </aside>

  <div class="workspace">
    <header class="topbar">
      <div class="breadcrumb">
        <span>Workspace</span><Icon name="chevron" size={12} /><strong
          >{active?.title ?? 'Overview'}</strong
        >
      </div>
      <div class="topbar-status">
        <span class="environment-pill"><span class="status-dot amber"></span>Demo workspace</span>
        <button
          class="topbar-methodology"
          onclick={() => methodology.showModal()}
          aria-label="Open benchmark methodology"
          title="Benchmark methodology"
          ><Icon name="book" size={17} /><span>Methodology</span></button
        >
      </div>
    </header>
    <main id="main-content" tabindex="-1">
      {#key page.url.pathname}
        <div
          class="page-content"
          in:fly={{ y: 5, duration: prefersReducedMotion.current ? 0 : 160 }}
        >
          {@render children()}
        </div>
      {/key}
    </main>
    <footer class="workspace-footer">
      <span>Q-Atlas <span class="footer-dash">/</span> Quantum computing, with context.</span><span
        >Local workspace <span class="status-dot"></span></span
      >
    </footer>
  </div>
</div>

<dialog bind:this={methodology} class="methodology-dialog" aria-labelledby="methodology-title">
  <div class="dialog-header">
    <p class="eyebrow">HOW TO READ THE EVIDENCE</p>
    <button class="icon-button" aria-label="Close methodology" onclick={() => methodology.close()}
      ><Icon name="close" /></button
    >
  </div>
  <h2 id="methodology-title">Compare fairly.<br />Interpret carefully.</h2>
  <p>
    Q-Atlas compares solutions to the same mathematical problem. Solution quality matters alongside
    runtime.
  </p>
  <ol>
    <li>
      <strong>One objective.</strong> QUBO values use canonical minimization. A larger Max-Cut is represented
      by a smaller, negative cost.
    </li>
    <li>
      <strong>Explicit timing.</strong> Simulator execution and total optimizer time must be reported
      separately once connected.
    </li>
    <li>
      <strong>Simulation has context.</strong> A classical simulation of a quantum circuit does not demonstrate
      hardware speedup.
    </li>
    <li>
      <strong>Know the source.</strong> All current charts and benchmark values are illustrative UI fixtures.
      They are not experimental evidence.
    </li>
  </ol>
  <button class="button primary" onclick={() => methodology.close()}
    >Return to workspace<Icon name="arrow" size={17} /></button
  >
</dialog>
