<script lang="ts">
  let {
    label,
    unit,
    help,
    min,
    max,
    value = $bindable(),
    integer = false
  }: {
    label: string;
    unit: string;
    help: string;
    min: number;
    max: number;
    value: number | undefined;
    integer?: boolean;
  } = $props();
  const id = $props.id();
</script>

<div class="parameter">
  <div class="parameter-label"><label for={id}>{label}</label><span title={help}>{unit}</span></div>
  <div class="inputs">
    <input
      type="range"
      aria-label={label + ' slider'}
      {min}
      {max}
      step={integer ? 1 : 'any'}
      value={value ?? min}
      oninput={(event) => (value = Number(event.currentTarget.value))}
      aria-describedby={id + '-help'}
    />
    <input
      type="number"
      {id}
      {min}
      {max}
      step={integer ? 1 : 'any'}
      bind:value
      aria-describedby={id + '-help'}
      required
    />
  </div>
  <small id={id + '-help'}>{help}</small>
</div>

<style>
  .parameter {
    margin: 22px 0;
  }
  .parameter-label,
  .inputs {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6em;
  }
  label {
    font-size: 13px;
    font-weight: 500;
  }
  .parameter-label span,
  small {
    color: var(--lab-muted);
    font-size: 11px;
  }
  .inputs {
    margin: 9px 0;
  }
  .inputs input[type='range'] {
    min-width: 0;
    width: 100%;
    accent-color: var(--blue);
  }
  input[type='number'] {
    width: 6.4em;
    min-width: 0;
    padding: 8px;
    background: var(--surface);
    color: inherit;
    border: 1px solid #bac7d7;
    border-radius: 2px;
    font: 12px var(--mono);
  }
  small {
    display: block;
    line-height: 1.45;
  }
</style>
