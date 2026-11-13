import type { OptimizationRequest } from '../../types/index.ts';
/** Dense weighted graph: real 16-bit enumeration, not a sleep or repeated dummy cost. */
export function largerWorkload(): OptimizationRequest['problem'] {
  return {
    kind: 'graph',
    num_vertices: 16,
    edges: Array.from({ length: 16 }, (_, i) =>
      Array.from({ length: 15 - i }, (_, k) => ({
        i,
        j: i + k + 1,
        coefficient: 1 + ((i * 17 + (i + k + 1) * 7) % 11)
      }))
    ).flat()
  };
}
