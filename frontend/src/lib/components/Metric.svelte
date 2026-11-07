<script lang="ts">
  let {
    label,
    value,
    unit = '',
    note,
    tone = 'neutral'
  }: {
    label: string;
    value: string | number;
    unit?: string;
    note: string;
    tone?: 'neutral' | 'cyan' | 'violet';
  } = $props();
</script>

<div class="measurement {tone}">
  <p class="eyebrow">{label}</p>
  <p class="value">{value}<span>{unit}</span></p>
  <p class="note">{note}</p>
</div>

<style>
  .measurement {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 18px 20px;
    min-width: 0;
    border-radius: 15px;
    box-shadow: 0 2px 7px #172b4d03;
  }
  .eyebrow {
    font-size: 9px;
  }
  .value {
    margin: 9px 0 5px;
    font:
      500 28px/1.2 'IBM Plex Sans',
      sans-serif;
    font-weight: 500;
    letter-spacing: -0.05em;
  }
  .value span {
    font-size: 13px;
    color: var(--muted);
    letter-spacing: normal;
    margin-left: 7px;
  }
  .note {
    font-size: 11px;
    color: var(--muted);
    margin: 0;
  }
  .cyan .value {
    color: var(--cyan);
  }
  .violet .value {
    color: var(--violet);
  }
</style>
