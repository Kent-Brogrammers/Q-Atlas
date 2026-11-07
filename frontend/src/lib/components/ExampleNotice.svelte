<script lang="ts">
  import Icon from './Icon.svelte';
</script>

<aside class="example-notice" aria-label="Data provenance">
  <Icon name="info" size={15} />
  <strong>Backend not connected</strong>
  <span
    >No experiments execute here. Optional example data is labeled and is not measured output.</span
  >
</aside>

<style>
  .example-notice {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    column-gap: 10px;
    row-gap: 4px;
    border: 1px solid #e2ebf5;
    background: #f7faff;
    padding: 9px 13px;
    border-radius: 4px;
    color: #69809b;
    font-size: 12px;
    line-height: 1.5;
  }
  strong {
    font:
      500 12px/1.5 'IBM Plex Sans',
      sans-serif;
    letter-spacing: normal;
    color: #4975a1;
  }
  span {
    color: #637285;
  }
</style>
