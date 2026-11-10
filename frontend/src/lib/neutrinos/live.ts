import type { NeutrinoRequest, NeutrinoResponse } from '../../types/index.ts';

export type Environment = 'vacuum' | 'matter' | 'layers' | 'density';
export interface LabSettings {
  environment: Environment;
  theta: number | undefined;
  delta_m2: number | undefined;
  energy: number | undefined;
  distance: number | undefined;
  potential: number | undefined;
  second_potential: number | undefined;
  max_potential: number | undefined;
  shots: number | undefined;
  samples: number | undefined;
  seed: number | undefined;
  particle: 'neutrino' | 'antineutrino';
}

export function defaultSettings(): LabSettings {
  return {
    environment: 'vacuum',
    theta: 0.2,
    delta_m2: 1,
    energy: 1,
    distance: 4,
    potential: 0.9210609940028851,
    second_potential: 1.4,
    max_potential: 1.8421219880057702,
    shots: 4096,
    samples: 21,
    seed: 42,
    particle: 'neutrino'
  };
}

export function buildRequest(settings: LabSettings): NeutrinoRequest {
  const bounds: [keyof LabSettings, number, number, boolean?][] = [
    ['theta', 0, Math.PI / 2],
    ['delta_m2', -10, 10],
    ['energy', 0.01, 100],
    ['distance', 0, 100],
    ['shots', 1, 100000, true],
    ['samples', 2, 41, true],
    ['seed', 0, 4294967295, true]
  ];
  if (settings.environment === 'matter' || settings.environment === 'layers')
    bounds.push(['potential', 0, 10]);
  if (settings.environment === 'layers') bounds.push(['second_potential', 0, 10]);
  if (settings.environment === 'density') bounds.push(['max_potential', 0, 10]);
  for (const [name, low, high, integer] of bounds) {
    const value = settings[name];
    if (
      typeof value !== 'number' ||
      !Number.isFinite(value) ||
      value < low ||
      value > high ||
      (integer && !Number.isInteger(value))
    )
      throw new Error(
        `${name} must be ${integer ? 'an integer' : 'a number'} from ${low} to ${high}.`
      );
  }
  if (settings.shots! * settings.samples! > 500000)
    throw new Error('Samples × shots must not exceed 500,000. Reduce either setting.');
  return {
    experiment: {
      parameters: {
        theta: settings.theta!,
        delta_m2: settings.delta_m2!,
        energy: settings.energy!,
        particle: settings.particle
      },
      layers:
        settings.environment === 'layers'
          ? [
              { distance: settings.distance! / 2, potential: settings.potential! },
              { distance: settings.distance! / 2, potential: settings.second_potential! }
            ]
          : [
              {
                distance: settings.distance!,
                potential: settings.environment === 'matter' ? settings.potential! : 0
              }
            ],
      shots: settings.shots!,
      seed: settings.seed!
    },
    axis: settings.environment === 'density' ? 'potential' : 'distance',
    samples: settings.samples!,
    max_potential: settings.environment === 'density' ? settings.max_potential! : 2,
    timeout_seconds: 30
  };
}

export const flavorChannels = [
  { key: 'electron', label: 'Electron νe', color: '#0f62fe' },
  { key: 'other', label: 'Other effective flavor νx', color: '#00869b' }
] as const;

/** Only project measured backend records into chart series; no physics is computed here. */
export function curveValues(
  result: NeutrinoResponse,
  flavor: 'electron' | 'other',
  source: 'numerical' | 'ideal' | 'measured'
) {
  return result.results.map((record) => record[source][flavor]);
}
