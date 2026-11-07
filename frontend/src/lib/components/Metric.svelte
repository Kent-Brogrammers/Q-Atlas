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
  let numerical = $derived(typeof value === 'number' || /^-?\d+(?:\.\d+)?$/.test(value));
</script>

<div class="measurement {tone}">
  <p class="eyebrow">{label}</p>
  <p class="value" class:unavailable={!numerical}>{value}<span>{unit}</span></p>
  <p class="note">{note}</p>
</div>

<style>
  .measurement {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 18px 20px;
    min-width: 0;
    border-radius: 4px;
    box-shadow: none;
  }
  .eyebrow {
    font-size: 12px;
  }
  .value {
    margin: 9px 0 5px;
    font: 400 26px/1.25 var(--mono);
    letter-spacing: normal;
  }
  .value span {
    font-size: 13px;
    color: var(--muted);
    letter-spacing: normal;
    margin-left: 7px;
  }
  .note {
    font-size: 12px;
    color: var(--muted);
    margin: 0;
  }
  .cyan .value {
    color: var(--cyan);
  }
  .violet .value {
    color: var(--violet);
  }
  .value.unavailable {
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: 2.3;
    color: var(--muted);
  }
</style>
