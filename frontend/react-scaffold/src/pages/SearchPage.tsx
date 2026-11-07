import { api } from '../api/client';
import RequestPanel from '../components/RequestPanel';
import type { SearchRequest } from '../types';

const initialRequest: SearchRequest = { num_qubits: 3, marked_states: ['101'], iterations: 2 };

export default function SearchPage() {
  return <RequestPanel title="Quantum search" description="Developer 4 workspace: compare success probability, oracle queries, and measured runtime separately." initialRequest={initialRequest} submit={api.search} />;
}
