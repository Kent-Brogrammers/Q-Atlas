/**
 * Discussion draft for Nick and Developer 5, NOT an approved API contract.
 * No endpoint or transport is registered. Replace these types with generated
 * OpenAPI types after the backend owners approve the model and wire format.
 */
import type { components } from '../../types/api.generated.ts';

type Schemas = components['schemas'];
type SharedProvenance = Pick<
  Schemas['OptimizationMetadata'],
  'seed' | 'repetitions' | 'timing_scope' | 'simulated' | 'simulation_method' | 'versions'
>;
export type ProposedEnvironment =
  | { kind: 'vacuum' }
  | { kind: 'constant_density'; density_g_cm3: number; electron_fraction: number };

export interface ProposedFlavor {
  id: string;
  label: string;
  symbol: string;
}

/** The backend declares actual supported channels; the UI has no default flavors. */
export interface ProposedNeutrinoModel {
  id: string;
  label: string;
  description: string;
  flavors: ProposedFlavor[];
  initial_flavor_ids: string[];
  environments: ProposedEnvironment['kind'][];
  assumptions: string[];
}

export interface ProposedNeutrinoRequest {
  model_id: string;
  initial_flavor_id: string;
  energy_gev: number;
  distance_km: number;
  distance_samples: number;
  environment: ProposedEnvironment;
  config: Schemas['RunConfig'];
}

export interface ProposedProbabilitySeries {
  flavor_id: string;
  classical: (number | null)[];
  qiskit: (number | null)[];
  absolute_error: (number | null)[];
}

/** Reuse established timing/solver fields without assigning probability an objective. */
export interface ProposedNeutrinoResult {
  status: 'completed';
  experiment: 'neutrinos';
  problem_id: string;
  backend: 'aer_simulator';
  model: ProposedNeutrinoModel;
  parameters: ProposedNeutrinoRequest;
  classical: Schemas['SolverResult'] | null;
  quantum: Schemas['SolverResult'] | null;
  distances_km: number[];
  series: ProposedProbabilitySeries[];
  metrics: {
    num_qubits: number | null;
    circuit_depth: number | null;
    shots_per_point: number | null;
    total_shots: number | null;
    max_absolute_error: number | null;
    rms_error: number | null;
    normalization_deviation: number | null;
    error_tolerance: number | null;
    within_tolerance: boolean | null;
  };
  metadata: SharedProvenance & {
    classical_method: string;
    qiskit_method: string;
    probability_method: 'statevector' | 'shots';
    parameter_source: string;
    physics_parameters: Record<string, { value: number; unit: string }>;
    state_encoding: Record<string, string>;
    unused_state_policy: string;
    circuit_depth_scope: string;
    assumptions: string[];
  };
}

/** Editable local settings can be incomplete. They are never submitted as a request. */
export interface NeutrinoSettingsDraft {
  model_id: string | null;
  initial_flavor_id: string | null;
  energy_gev: number | undefined;
  distance_km: number | undefined;
  environment_kind: ProposedEnvironment['kind'];
  density_g_cm3: number | undefined;
  electron_fraction: number | undefined;
  requested_shots: number | undefined;
}
