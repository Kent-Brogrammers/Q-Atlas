import type { NeutrinoRecord } from '../../types/index.ts';

/** Sum only disjoint point timers; ideal execution is nested in circuit workflow. */
export function neutrinoTimings(points: Pick<NeutrinoRecord, 'timing_ms'>[]) {
  return points.reduce(
    (total, point) => ({
      classicalMs: total.classicalMs + point.timing_ms.classical,
      circuitMs: total.circuitMs + point.timing_ms.circuit_end_to_end,
      idealMs: total.idealMs + point.timing_ms.ideal_execution
    }),
    { classicalMs: 0, circuitMs: 0, idealMs: 0 }
  );
}
