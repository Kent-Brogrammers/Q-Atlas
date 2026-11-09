import selection from '../../../examples/compiler/programs/weighted_selection.py?raw';
import maximize from '../../../examples/compiler/programs/weighted_maximize.py?raw';
import helper from '../../../examples/compiler/programs/rejected_helper_call.py?raw';
import loop from '../../../examples/compiler/programs/rejected_dynamic_loop.py?raw';
import higherOrder from '../../../examples/compiler/programs/rejected_higher_order.py?raw';

// These are source-text fixtures, never Python modules or fabricated API responses.
export const PROGRAM_EXAMPLES = [
  { filename: 'weighted_selection.py', label: 'Weighted selection · expected support', source: selection },
  { filename: 'weighted_maximize.py', label: 'Weighted maximization · expected support', source: maximize },
  { filename: 'rejected_helper_call.py', label: 'Helper call · expected rejection', source: helper },
  { filename: 'rejected_dynamic_loop.py', label: 'Dynamic loop · expected rejection', source: loop },
  { filename: 'rejected_higher_order.py', label: 'Cubic objective · expected rejection', source: higherOrder },
] as const;
