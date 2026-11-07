<script lang="ts">
  import { page } from '$app/state';
  import Icon from '#lib/components/Icon.svelte';
</script>

<svelte:head><title>{page.status} · Q-Atlas</title></svelte:head>
<div class="page-heading">
  <div>
    <p class="eyebrow">WORKSPACE / {page.status}</p>
    <h1>This view is unavailable.</h1>
    <p>Return to the overview to choose an experiment.</p>
  </div>
</div>
<a class="button primary" href="/">Open overview<Icon name="arrow" size={16} /></a>
