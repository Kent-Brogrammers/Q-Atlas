import { api } from '../api/client';
import RequestPanel from '../components/RequestPanel';
import type { MaterialsRequest } from '../types';

const initialRequest: MaterialsRequest = { model: 'ising', num_spins: 2, coupling: 1, field: 0.5, boundary: 'open', observable: 'energy' };

export default function MaterialsPage() {
  return <RequestPanel title="Quantum materials" description="Developer 1 workspace: small spin models compared with an exact classical reference." initialRequest={initialRequest} submit={api.materials} />;
}
