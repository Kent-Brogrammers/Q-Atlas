/** Display measured durations without rounding short work to a misleading zero. */
export function duration(ms: number | null | undefined): string {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return 'Not measured';
  const [value, unit] =
    ms === 0
      ? [0, 'ms']
      : ms < 0.001
        ? [ms * 1_000_000, 'ns']
        : ms < 1
          ? [ms * 1000, 'µs']
          : ms < 1000
            ? [ms, 'ms']
            : [ms / 1000, 's'];
  return `${Number(value).toLocaleString('en-US', { maximumFractionDigits: 3 })} ${unit}`;
}
export function number(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return 'Not measured';
  return value.toLocaleString('en-US', { maximumFractionDigits: 6 });
}
