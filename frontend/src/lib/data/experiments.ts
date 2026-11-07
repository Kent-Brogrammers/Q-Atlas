import type { Experiment } from '../types/contracts.ts';

export const experiments: {
  id: Experiment;
  number: string;
  title: string;
  short: string;
  description: string;
  method: string;
  icon: string;
  color: string;
}[] = [
  {
    id: 'compiler',
    number: '01',
    title: 'Python Compiler',
    short: 'Compiler',
    description: 'Edit a binary Python objective and inspect an example QUBO.',
    method: 'AST → QUBO → circuit',
    icon: 'code',
    color: 'blue'
  },
  {
    id: 'materials',
    number: '02',
    title: 'Quantum Materials',
    short: 'Materials',
    description: 'Set spin count, coupling, and field parameters for a small spin system.',
    method: 'Spin Hamiltonian · exact reference',
    icon: 'atom',
    color: 'violet'
  },
  {
    id: 'optimization',
    number: '03',
    title: 'Optimization',
    short: 'Optimization',
    description: 'Configure Max-Cut inputs and inspect classical and QAOA example data.',
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
