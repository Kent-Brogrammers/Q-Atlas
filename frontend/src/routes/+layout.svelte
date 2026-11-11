<script lang="ts">
  import '../app.css';
  import '@fontsource/ibm-plex-sans/latin-400.css';
  import '@fontsource/ibm-plex-sans/latin-500.css';
  import '@fontsource/ibm-plex-sans/latin-600.css';
  import '@fontsource/ibm-plex-mono/latin-400.css';
  import { page } from '$app/state';
  import { fly } from 'svelte/transition';
  import { prefersReducedMotion } from 'svelte/motion';
  import { onMount, type Snippet } from 'svelte';
  import { primaryNavigation } from '#lib/data/navigation.ts';
  import { experiments } from '#lib/data/experiments.ts';
  import Icon from '#lib/components/Icon.svelte';
  import Logo from '#lib/components/Logo.svelte';

  let { children }: { children: Snippet } = $props();
  let dark = $state(false);
  onMount(() => {
    dark = document.documentElement.dataset.theme === 'dark';
  });
  function toggleTheme() {
    dark = !dark;
    const theme = dark ? 'dark' : 'light';
    document.documentElement.dataset.theme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', dark ? '#1a1715' : '#f5f0eb');
    try {
      localStorage.setItem('q-atlas-theme', theme);
    } catch {
      // The current tab can still change theme with storage disabled.
    }
  }
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
      <button class="theme-switch" role="switch" aria-checked={dark} onclick={toggleTheme}>
        Dark mode <span class="track" aria-hidden="true"></span>
      </button>
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

<style>
  .theme-switch {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    min-height: 44px;
    flex-shrink: 0;
    font-size: 0.85rem;
  }
  .track {
    display: flex;
    align-items: center;
    width: 2rem;
    height: 1.15rem;
    padding: 2px;
    border: 1px solid var(--muted);
    border-radius: 1rem;
    background: var(--surface);
  }
  .track::after {
    content: '';
    width: 0.75rem;
    height: 0.75rem;
    border-radius: 50%;
    background: var(--muted);
  }
  [aria-checked='true'] .track {
    justify-content: flex-end;
    background: var(--blue);
    border-color: var(--blue);
  }
  [aria-checked='true'] .track::after {
    background: var(--bg);
  }
</style>
