<script lang="ts">
  let { compact = false }: { compact?: boolean } = $props();
</script>

<figure class:compact>
  <svg
    viewBox="0 0 520 156"
    role="img"
    aria-label="Conceptual QAOA circuit layout: Hadamard preparation, cost layer, mixer layer, and measurement. This is a schematic, not a generated circuit."
  >
    <title>QAOA layer schematic — conceptual illustration</title>
    {#each [0, 1, 2] as i}
      {@const y = 35 + i * 39}
      <text class="qubit" x="8" y={y + 4}>q{i}</text><line
        x1="43"
        x2="493"
        y1={y}
        y2={y}
        stroke="#d5e1ee"
      />
      <rect x="64" y={y - 12} width="25" height="24" fill="#edf4ff" stroke="#9fbee2" /><text
        x="77"
        y={y + 4}
        text-anchor="middle">H</text
      >
      <rect x="333" y={y - 12} width="56" height="24" fill="#f3eefb" stroke="#b49bcf" /><text
        x="361"
        y={y + 4}
        text-anchor="middle">RX(β)</text
      >
      <rect x="448" y={y - 12} width="26" height="24" fill="#f3f6fb" stroke="#bdcde0" /><path
        d={`M453 ${y + 5}q8-15 16 0m-8 0 4-10`}
        stroke="#728ba9"
        fill="none"
      />
    {/each}
    <rect
      x="154"
      y="14"
      width="112"
      height="120"
      fill="#eff9fc"
      stroke="#a4d4df"
      stroke-dasharray="3 3"
    /><text x="210" y="70" text-anchor="middle" class="cost">U(C, γ)</text><text
      x="210"
      y="89"
      text-anchor="middle"
      class="annotation">cost layer</text
    >
    <text x="362" y="151" text-anchor="middle" class="annotation">mixer</text>
  </svg>
  {#if !compact}<figcaption>Conceptual layer layout · not a compiled circuit</figcaption>{/if}
</figure>

<style>
  figure {
    margin: 0;
    padding: 16px 20px;
  }
  svg {
    width: 100%;
    display: block;
  }
  text {
    font: 10px var(--mono);
    fill: #4c6485;
  }
  .qubit {
    fill: #8395ad;
  }
  .cost {
    fill: #4d98a8;
    font-size: 13px;
  }
  .annotation {
    fill: #8a9bb0;
    font-size: 8px;
  }
  figcaption {
    color: var(--muted);
    font: 9px var(--mono);
    margin-top: 12px;
  }
  .compact {
    padding: 0;
  }
</style>
