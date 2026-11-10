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
    content="Q-Atlas: Python objective compilation, generated circuit code, and the Neutrino Oscillation Lab."
  />
</svelte:head>

<a class="skip-link" href="#main-content">Skip to workspace</a>
<div class="app-shell">
  <aside class="sidebar" aria-label="Workspace navigation">
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
          title={item.title}
        >
          <Icon name={item.icon} /><span>{item.title}</span><span class="mobile-nav-label"
            >{item.title}</span
          >
        </a>
      {/each}
    </nav>
  </aside>
  <div class="workspace">
    <header class="topbar">
      <div class="breadcrumb">
        <span>Q-Atlas</span><Icon name="chevron" size={12} /><strong>{title}</strong>
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
  </div>
</div>
