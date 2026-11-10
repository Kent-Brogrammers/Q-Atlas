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
  <p>Example counts <span class="mono">n = {total.toLocaleString()}</span></p>
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
    font-size: 12px;
  }
  .mono {
    color: var(--text);
    font-size: 12px;
  }
  .cut-label {
    font:
      12px 'IBM Plex Sans',
      sans-serif;
    color: var(--muted);
    margin-left: 5px;
  }
  .track {
    height: 10px;
    border-radius: 4px;
    background: var(--surface);
  }
  .bar {
    border-radius: 4px;
    height: 100%;
    background: var(--blue);
    transition: width 0.2s;
    min-width: 2px;
  }
  .bar.best {
    background: var(--accent);
  }
  .percentage {
    font: 12px var(--mono);
    text-align: right;
    color: var(--text);
  }
  p {
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin: 22px 0 0;
    padding-top: 13px;
    color: var(--muted);
    font-size: 12px;
  }
</style>
