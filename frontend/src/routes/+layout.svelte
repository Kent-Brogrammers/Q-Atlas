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
  import { primaryNavigation } from '#lib/data/navigation.ts';
  import { experiments } from '#lib/data/experiments.ts';
  import Icon from '#lib/components/Icon.svelte';
  import Logo from '#lib/components/Logo.svelte';

  let { children }: { children: Snippet } = $props();
  let active = $derived(primaryNavigation.find((item) => page.url.pathname === item.href));
  // Retained experiment routes still have accurate breadcrumbs when opened directly.
  let title = $derived(
    active?.title ??
      experiments.find((item) => page.url.pathname === `/${item.id}/`)?.title ??
      'Workspace'
  );
</script>

<svelte:head>
  <meta
    name="description"
    content="Q-Atlas studies neutrino oscillations for Quantum for Science, with independent classical validation and a supporting Python optimization compiler."
  />
</svelte:head>

<a class="skip-link" href="#main-content">Skip to workspace</a>
<div class="app-shell">
  <aside id="workspace-navigation" class="sidebar" aria-label="Workspace navigation" tabindex="-1">
    <a class="brand" href="/" aria-label="Q-Atlas overview"
      ><Logo /><span>Q<span class="brand-dash">—</span>Atlas<span class="brand-dot">.</span></span
      ></a
    >
    <nav aria-label="Main navigation">
      {#each primaryNavigation as item}
        <a
          class:active={active?.href === item.href}
          href={item.href}
          aria-current={active?.href === item.href ? 'page' : undefined}
          aria-label={item.title}
          title={item.title}
        >
          <Icon name={item.icon} /><span>{item.title}</span><span class="mobile-nav-label"
            >{item.mobileTitle}</span
          >
        </a>
      {/each}
    </nav>
  </aside>
  <div class="workspace">
    <header class="topbar">
      <div class="breadcrumb">
        <a href="/" aria-label="Back to overview">Q-Atlas</a><Icon
          name="chevron"
          size={12}
        /><strong>{title}</strong>
      </div>
      <a class="navigation-return" href="#workspace-navigation">Navigation ↑</a>
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
  </div>
</div>
