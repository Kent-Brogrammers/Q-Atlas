import neutrino from '../../../examples/compiler/programs/neutrino_simulation.py?raw';
import three from '../../../examples/compiler/programs/portfolio_3.py?raw';
import four from '../../../examples/compiler/programs/portfolio_4.py?raw';
import five from '../../../examples/compiler/programs/portfolio_5.py?raw';
import six from '../../../examples/compiler/programs/portfolio_6.py?raw';
import maxcut from '../../../examples/compiler/programs/stress_maxcut_6.py?raw';
import partition from '../../../examples/compiler/programs/stress_partition_6.py?raw';
import conflicts from '../../../examples/compiler/programs/stress_conflicts_6.py?raw';

// These are source-text fixtures, never Python modules or fabricated API responses.
export const PROGRAM_EXAMPLES = [
  {
    filename: 'neutrino_simulation.py',
    label: 'Neutrino simulation · matter resonance',
    source: neutrino
  },
  { filename: 'portfolio_3.py', label: '3 qubits · choose 1 energy project', source: three },
  { filename: 'portfolio_4.py', label: '4 qubits · choose 2 energy projects', source: four },
  { filename: 'portfolio_5.py', label: '5 qubits · choose 2 energy projects', source: five },
  { filename: 'portfolio_6.py', label: '6 qubits · choose 3 energy projects', source: six },
  { filename: 'stress_maxcut_6.py', label: '6 qubits · dense weighted Max-Cut', source: maxcut },
  { filename: 'stress_partition_6.py', label: '6 qubits · balance workloads', source: partition },
  {
    filename: 'stress_conflicts_6.py',
    label: '6 qubits · competing task selections',
    source: conflicts
  }
] as const;
