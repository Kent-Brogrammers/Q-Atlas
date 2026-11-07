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
    color: var(--blue-light);
    border-color: #d6e7fd;
    background: #eff6ff;
  }
  .cyan {
    color: var(--cyan);
    border-color: #d5edf4;
    background: #edf9fc;
  }
  .violet {
    color: var(--violet);
    border-color: #e6ddf3;
    background: #f6f1fc;
  }
  .amber {
    color: #a87930;
    border-color: #f0e2c3;
    background: #fffaf0;
  }
</style>
