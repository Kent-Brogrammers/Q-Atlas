<script lang="ts">
  import type { Snippet } from 'svelte';
  let { title, description, children }: { title: string; description: string; children?: Snippet } =
    $props();
</script>

<section class="feature-banner" aria-label={title}>
  <h2>{title}</h2>
  <p>{description}</p>
  {#if children}<div class="banner-footer">{@render children()}</div>{/if}
</section>

<style>
  .feature-banner {
    padding: 24px;
    min-height: 176px;
    color: var(--bg);
    border-radius: 4px;
    background: var(--blue);
  }
  h2 {
    margin: 0 0 12px;
    font:
      400 24px/1.25 'IBM Plex Sans',
      sans-serif;
    color: var(--bg);
  }
  p {
    max-width: 800px;
    margin: 0;
    color: var(--bg);
    font:
      400 14px/1.6 'IBM Plex Sans',
      sans-serif;
  }
  .banner-footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 20px;
  }
  .banner-footer :global(a) {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    padding: 9px 12px;
    border-radius: 2px;
    border: 1px solid var(--bg);
    color: var(--blue);
    background: var(--bg);
    font-size: 14px;
  }
  .banner-footer :global(a:hover) {
    background: var(--surface-raised);
  }
  @media (max-width: 480px) {
    .feature-banner {
      padding: 20px;
    }
    h2 {
      font-size: 22px;
    }
  }
</style>
