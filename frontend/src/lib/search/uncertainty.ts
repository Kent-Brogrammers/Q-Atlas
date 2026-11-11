import type { SearchResult } from '../../types/index.ts';

// Two-sided 95% Wilson score interval, without continuity correction.
// https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
export function wilson95(successes: number, shots: number): [number, number] {
  if (
    !Number.isSafeInteger(shots) ||
    shots < 1 ||
    !Number.isSafeInteger(successes) ||
    successes < 0 ||
    successes > shots
  ) {
    throw new Error('Sampling intervals require integer successful shots from 0 to total shots.');
  }
  const z = 1.959963984540054;
  const z2 = z * z;
  const p = successes / shots;
  const denominator = 1 + z2 / shots;
  const center = (p + z2 / (2 * shots)) / denominator;
  const halfWidth = (z * Math.sqrt((p * (1 - p)) / shots + z2 / (4 * shots * shots))) / denominator;
  return [
    successes === 0 ? 0 : Math.max(0, center - halfWidth),
    successes === shots ? 1 : Math.min(1, center + halfWidth)
  ];
}

export function samplingInterval(result: SearchResult): [number, number] | null {
  const { successful_shots: successes, shots, success_probability: probability } = result.metrics;
  // Older API records can lack counts. Never infer them from a rounded probability.
  if (successes == null || shots == null) return null;
  const interval = wilson95(successes, shots);
  if (
    probability != null &&
    (!Number.isFinite(probability) || Math.abs(probability - successes / shots) > 1e-12)
  ) {
    throw new Error('The measured probability disagrees with the successful-shot count.');
  }
  return interval;
}

export function intervalLabel(interval: [number, number] | null): string {
  return interval === null
    ? 'Not available'
    : `${(interval[0] * 100).toFixed(2)}%–${(interval[1] * 100).toFixed(2)}%`;
}
