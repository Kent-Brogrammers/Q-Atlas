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
    description: 'From a Python objective to a quantum-ready problem.',
    method: 'AST → QUBO → circuit',
    icon: 'code',
    color: 'blue'
  },
  {
    id: 'materials',
    number: '02',
    title: 'Quantum Materials',
    short: 'Materials',
    description: 'Small spin systems. A closer look at quantum matter.',
    method: 'Spin Hamiltonian · exact reference',
    icon: 'atom',
    color: 'violet'
  },
  {
    id: 'optimization',
    number: '03',
    title: 'Optimization',
    short: 'Optimization',
    description: 'One problem. Two approaches. Evidence side by side.',
    method: 'Max-Cut · QAOA · classical',
    icon: 'graph',
    color: 'cyan'
  },
  {
    id: 'search',
    number: '04',
    title: 'Quantum Search',
    short: 'Search',
    description: 'Explore amplitude amplification, one iteration at a time.',
    method: 'Grover · probability · queries',
    icon: 'search',
    color: 'teal'
  }
];
