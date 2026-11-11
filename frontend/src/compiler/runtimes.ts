export interface RuntimeMeasurement {
  label: string;
  kind: 'classical' | 'qpu';
  milliseconds: number;
}

// Unknown readings are omitted, never replaced by zero. Keep both paths in ms.
export function runtimeMeasurements(
  classicalMs?: number | null,
  quantumSeconds?: number | null
): RuntimeMeasurement[] {
  const rows: RuntimeMeasurement[] = [];
  if (typeof classicalMs === 'number' && Number.isFinite(classicalMs) && classicalMs >= 0)
    rows.push({ label: 'Classical solve', kind: 'classical', milliseconds: classicalMs });
  if (typeof quantumSeconds === 'number') {
    const milliseconds = quantumSeconds * 1000;
    if (Number.isFinite(milliseconds) && milliseconds >= 0)
      rows.push({ label: 'IBM QPU usage', kind: 'qpu', milliseconds });
  }
  return rows;
}
