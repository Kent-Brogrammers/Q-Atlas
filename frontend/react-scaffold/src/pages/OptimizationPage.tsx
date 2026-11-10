import { api } from '../api/client';
import RequestPanel from '../components/RequestPanel';
import type { OptimizationRequest } from '../types';

const initialRequest: OptimizationRequest = {
  problem: { kind: 'qubo', qubo: { num_variables: 3, constant: 0, linear: [10, 20, 0], quadratic: [{ i: 0, j: 1, coefficient: 15 }], sense: 'minimize', original_sense: 'minimize' } },
};

export default function OptimizationPage() {
  return <RequestPanel title="Optimization" description="Developer 3 workspace: QAOA and classical baselines for the same graph or QUBO." initialRequest={initialRequest} submit={api.optimization} />;
}
