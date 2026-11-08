import type {
  NeutrinoSettingsDraft,
  ProposedFlavor,
  ProposedNeutrinoResult,
  ProposedProbabilitySeries
} from './proposal.ts';

export function initialSettings(): NeutrinoSettingsDraft {
  return {
    model_id: null,
    initial_flavor_id: null,
    energy_gev: 1,
    distance_km: 1000,
    environment_kind: 'vacuum',
    density_g_cm3: undefined,
    electron_fraction: undefined,
    requested_shots: 1024
  };
}

/** Input hygiene only. Physical validation and model limits belong to the backend. */
export function settingsErrors(draft: NeutrinoSettingsDraft): string[] {
  const errors: string[] = [];
  if (!Number.isFinite(draft.energy_gev) || draft.energy_gev! <= 0)
    errors.push('Energy must be a finite number greater than zero.');
  if (!Number.isFinite(draft.distance_km) || draft.distance_km! < 0)
    errors.push('Propagation distance must be a finite, nonnegative number.');
  if (
    !Number.isInteger(draft.requested_shots) ||
    draft.requested_shots! < 1 ||
    draft.requested_shots! > 100000
  )
    errors.push('Requested shots must be an integer from 1 to 100,000.');
  if (draft.environment_kind === 'constant_density') {
    if (!Number.isFinite(draft.density_g_cm3) || draft.density_g_cm3! < 0)
      errors.push('Matter density must be a finite, nonnegative number.');
    if (
      !Number.isFinite(draft.electron_fraction) ||
      draft.electron_fraction! < 0 ||
      draft.electron_fraction! > 1
    )
      errors.push('Electron fraction must be a finite number between zero and one.');
  }
  return errors;
}

export function exportSettings(draft: NeutrinoSettingsDraft) {
  const errors = settingsErrors(draft);
  if (errors.length) throw new Error(errors.join(' '));
  return {
    kind: 'neutrino_configuration_draft' as const,
    contract_status: 'proposal_not_approved' as const,
    notice: 'Local settings only. No experiment executed; no API request or result is included.',
    model_id: draft.model_id,
    initial_flavor_id: draft.initial_flavor_id,
    energy_gev: draft.energy_gev,
    distance_km: draft.distance_km,
    environment:
      draft.environment_kind === 'vacuum'
        ? { kind: 'vacuum' as const }
        : {
            kind: 'constant_density' as const,
            density_g_cm3: draft.density_g_cm3,
            electron_fraction: draft.electron_fraction
          },
    requested_shots: draft.requested_shots
  };
}

export interface DisplaySeries {
  flavor: ProposedFlavor;
  values: ProposedProbabilitySeries;
}

/** Display only declared channels with aligned, finite probabilities; never fill missing values. */
export function displaySeries(result: ProposedNeutrinoResult | null): DisplaySeries[] {
  if (!result || !result.distances_km.length) return [];
  const distances = result.distances_km;
  if (distances.some((x, i) => !Number.isFinite(x) || x < 0 || (i > 0 && x <= distances[i - 1])))
    return [];
  return result.model.flavors.flatMap((flavor) => {
    const matches = result.series.filter((series) => series.flavor_id === flavor.id);
    if (matches.length !== 1) return [];
    const values = matches[0];
    const valid = [values.classical, values.qiskit].every(
      (samples) =>
        samples.length === distances.length &&
        samples.every((p) => p === null || (Number.isFinite(p) && p >= 0 && p <= 1))
    );
    return valid ? [{ flavor, values }] : [];
  });
}

export function formatValue(value: number | null | undefined, digits = 6): string {
  if (value == null || !Number.isFinite(value)) return '—';
  if (value === 0) return '0';
  return Math.abs(value) < 0.0001
    ? value.toExponential(2)
    : Number(value.toFixed(digits)).toLocaleString('en-US');
}

/** SVG coordinate projection, not a neutrino calculation. Nulls break the path. */
export function probabilityPath(
  distances: number[],
  probabilities: (number | null)[],
  extent: number
): string {
  let connected = false;
  return probabilities
    .map((p, i) => {
      if (p === null) {
        connected = false;
        return '';
      }
      const command = connected ? 'L' : 'M';
      connected = true;
      return `${command}${64 + (distances[i] / (extent || 1)) * 754},${272 - p * 230}`;
    })
    .filter(Boolean)
    .join(' ');
}
