import type { SearchResult } from '../../types/index.ts';

export function gateResources(result: SearchResult): { total: number; breakdown: string } | null {
  const counts = result.metrics.circuit_gate_counts;
  if (counts == null) return null;
  const entries = Object.entries(counts).sort(([a], [b]) => a.localeCompare(b));
  let total = 0;
  for (const [name, count] of entries) {
    if (!name.length || !Number.isSafeInteger(count) || count < 1) {
      throw new Error('The backend reported invalid circuit gate counts.');
    }
    total += count;
  }
  if (!Number.isSafeInteger(total))
    throw new Error('Circuit gate total exceeds the safe integer range.');
  return {
    total,
    breakdown: entries.map(([name, count]) => `${name}: ${count}`).join(' · ') || 'No gates'
  };
}
