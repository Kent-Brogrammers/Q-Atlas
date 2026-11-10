<script lang="ts">
  import type { Snippet } from 'svelte';
  let {
    tone = 'neutral',
    children
  }: { tone?: 'neutral' | 'blue' | 'cyan' | 'violet' | 'amber'; children: Snippet } = $props();
</script>

<span class="badge {tone}">{@render children()}</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 9px;
    border-radius: 4px;
    border: 1px solid var(--border);
    font:
      500 12px/1.2 'IBM Plex Sans',
      sans-serif;
    letter-spacing: normal;
    white-space: nowrap;
    color: var(--muted);
    background: var(--surface);
  }
  .blue {
    color: var(--blue);
    border-color: var(--border);
    background: var(--surface);
  }
  .cyan {
    color: var(--accent);
    border-color: var(--border);
    background: var(--surface);
  }
  .violet {
    color: var(--violet);
    border-color: var(--border);
    background: var(--surface);
  }
  .amber {
    color: var(--accent);
    border-color: var(--border);
    background: var(--surface);
  }
</style>
