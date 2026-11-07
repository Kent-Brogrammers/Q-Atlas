<script lang="ts">
  let { bins }: { bins: { cut: number; count: number }[] } = $props();
  let total = $derived(bins.reduce((sum, bin) => sum + bin.count, 0));
</script>

<div class="histogram">
  {#each bins as bin, i}
    <div class="distribution-row">
      <span class="mono">{bin.cut}<span class="cut-label">edges</span></span>
      <div class="track">
        <div class="bar" class:best={i === 0} style:width={`${(bin.count / total) * 100}%`}></div>
      </div>
      <span class="percentage">{((bin.count / total) * 100).toFixed(1)}%</span>
    </div>
  {/each}
  <p>Cut size distribution <span class="mono">n = {total.toLocaleString()}</span></p>
</div>

<style>
  .histogram {
    padding: 10px 24px 20px;
  }
  .distribution-row {
    display: grid;
    grid-template-columns: 46px 1fr 43px;
    gap: 13px;
    align-items: center;
    margin-bottom: 17px;
    font-size: 10px;
  }
  .mono {
    color: #526b88;
    font-size: 10px;
  }
  .cut-label {
    font:
      8px 'IBM Plex Sans',
      sans-serif;
    color: #677383;
    margin-left: 5px;
  }
  .track {
    height: 10px;
    border-radius: 5px;
    background: #f0f5fb;
  }
  .bar {
    border-radius: 5px;
    height: 100%;
    background: #b7cae4;
    transition: width 0.2s;
    min-width: 2px;
  }
  .bar.best {
    background: #75b6e6;
  }
  .percentage {
    font: 9px var(--mono);
    text-align: right;
    color: #60738b;
  }
  p {
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin: 22px 0 0;
    padding-top: 13px;
    color: #677282;
    font-size: 10px;
  }
</style>
