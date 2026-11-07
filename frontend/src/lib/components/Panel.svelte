<script lang="ts">
  import type { Snippet } from 'svelte';
  let {
    title,
    kicker,
    subtitle,
    toolbar,
    children,
    className = ''
  }: {
    title: string;
    kicker?: string;
    subtitle?: string;
    toolbar?: Snippet;
    children: Snippet;
    className?: string;
  } = $props();
  const id = $props.id();
</script>

<section class="panel {className}" aria-labelledby={id}>
  <header class="panel-heading">
    <div>
      {#if kicker}<p class="eyebrow">{kicker}</p>{/if}
      <h2 {id}>{title}</h2>
      {#if subtitle}<p class="panel-subtitle">{subtitle}</p>{/if}
    </div>
    {#if toolbar}<div class="panel-toolbar">{@render toolbar()}</div>{/if}
  </header>
  {@render children()}
</section>

<style>
  .panel-heading {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    padding: 22px 24px 18px;
  }
  h2 {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
    letter-spacing: normal;
  }
  .eyebrow {
    margin: 0 0 10px;
  }
  .panel-subtitle {
    margin: 5px 0 0;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.5;
  }
  .panel-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  @media (max-width: 600px) {
    .panel-heading {
      padding: 18px;
      gap: 10px;
    }
  }
</style>
