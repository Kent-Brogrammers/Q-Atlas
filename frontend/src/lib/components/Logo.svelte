<script lang="ts">
  let { size = 34 }: { size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
  <g stroke="currentColor" stroke-width="1.6" stroke-linejoin="round">
    <path d="M24 5 41 15v19L24 44 7 34V15Z" />
    <path d="m7 15 17 10 17-10M24 25v19M24 5v20M7 34l17-9 17 9" />
  </g>
  <circle cx="24" cy="25" r="4" fill="currentColor" />
</svg>
