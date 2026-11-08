<script lang="ts">
  let { name, size = 20 }: { name: string; size?: number } = $props();
  const paths: Record<string, string> = {
    activity: 'M3 12h4l3-7 4 14 3-7h4',
    home: 'M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z',
    code: 'm8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 20',
    atom: 'M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z',
    graph:
      'M6 5a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM18 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM6 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM18 15a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM8 6l8-1M6 9v8M18 7v8M8 18l8-1M8 8l8 7',
    search: 'M10.5 3a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15Zm5.5 13 5 5',
    arrow: 'M4 12h16m-6-6 6 6-6 6',
    northeast: 'M6 18 18 6M6 6h12v12',
    chevron: 'm9 5 7 7-7 7',
    plus: 'M12 5v14M5 12h14',
    minus: 'M5 12h14',
    reset: 'M3 10a9 9 0 1 1 2 8M3 4v6h6',
    fit: 'M8 3H3v5m13-5h5v5M3 16v5h5m8 0h5v-5',
    sliders: 'M4 7h4m4 0h8M4 17h10m4 0h2M8 4v6m6 4v6',
    book: 'M12 5C8 2 3 4 3 4v15s5-2 9 1c4-3 9-1 9-1V4s-5-2-9 1Zm0 0v15',
    info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 7v7m0-10v.01',
    close: 'm6 6 12 12M6 18 18 6',
    copy: 'M9 8h11v13H9zM15 8V3H4v13h5',
    download: 'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
    check: 'm5 12 4 4L19 6',
    clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4v5l3 2',
    terminal: 'm4 6 6 6-6 6m9 0h7',
    circuit: 'M2 6h20M2 18h20M6 3h6v6H6zm7 12h6v6h-6zM16 6v9',
    layers: 'm12 3 10 5-10 5L2 8Zm-9 10 9 5 9-5M3 18l9 5 9-5'
  };
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.5"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
>
  <path d={paths[name] ?? paths.graph} />
</svg>
