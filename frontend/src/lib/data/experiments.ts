import type { Experiment } from '../types/contracts.ts';

// Retained workspace catalog, separate from the focused primary navigation.
// These UI IDs do not extend the approved backend experiment discriminator.
export type WorkspaceView = Experiment | 'neutrinos';

export const experiments: {
  id: WorkspaceView;
  number: string;
  title: string;
  short: string;
  description: string;
  method: string;
  icon: string;
  color: string;
}[] = [
  {
    id: 'neutrinos',
    number: '05',
    title: 'Neutrino Oscillations',
    short: 'Neutrinos',
    description:
      'Configure neutrino propagation and inspect backend-provided flavor probabilities.',
    method: 'Vacuum · constant-density matter · accuracy',
    icon: 'activity',
    color: 'blue'
  },
  {
    id: 'compiler',
    number: '01',
    title: 'Python Compiler',
    short: 'Compiler',
    description:
      'Convert a marked Python objective into verified circuit code and download the script.',
    method: 'AST → QUBO → circuit',
    icon: 'code',
    color: 'blue'
  },
  {
    id: 'materials',
    number: '02',
    title: 'Quantum Materials',
    short: 'Materials',
    description: 'Spin-system controls for the existing Ising-chain experiment.',
    method: 'Spin Hamiltonian · exact reference',
    icon: 'atom',
    color: 'violet'
  },
  {
    id: 'optimization',
    number: '03',
    title: 'Optimization',
    short: 'Optimization',
    description: 'Compare measured local QAOA results with the exact classical Max-Cut optimum.',
    method: 'Max-Cut · QAOA · classical',
    icon: 'graph',
    color: 'cyan'
  },
  {
    id: 'search',
    number: '04',
    title: 'Quantum Search',
    short: 'Search',
    description: 'Configure a search space and select a marked state for Grover’s algorithm.',
    method: 'Grover · probability · queries',
    icon: 'search',
    color: 'teal'
  }
];
