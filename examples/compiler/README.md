# Compiler source examples

These `.py` files are input text, not executable Python modules. Paste their contents
into the compiler editor or send them as the `source` field to
`POST /api/compiler/analyze`. Do not run or import them: `qatlas.objective` is a marker
inspected by the parser, with no runtime decorator package required.

All seven examples should return `status=supported`, a normalized QUBO matching
[expected_qubos.json](expected_qubos.json), and an unexecuted symbolic circuit preview.
The JSON contains mathematical expectations, not sampled or measured solver results.

| Source | Purpose | Expected canonical coefficients |
| --- | --- | --- |
| [minimize_three_bits.py](minimize_three_bits.py) | Constant, linear, and pair terms | Constant 5, linear [-2,0,0], pair (0,2)=3 |
| [maximize_three_bits.py](maximize_three_bits.py) | Negate every coefficient for maximization | Constant -5, linear [2,0,0], pair (1,2)=-1 |
| [repeated_terms.py](repeated_terms.py) | Fold binary squares and combine reversed pair factors | Constant 2, linear [-2,0,0], pair (0,1)=1 |
| [six_bits.py](six_bits.py) | Largest supported source width, verified on 64 inputs | Constant 9, linear [-1,-2,-3,-4,-5,-6], pairs (0,5)=2 and (1,4)=1 |
| [local_assignments.py](local_assignments.py) | Docstring, named weights/terms, sequential reassignment | Constant 5, linear [-2,-1,0], pair (0,2)=3 |
| [bounded_loops.py](bounded_loops.py) | Fixed ranges, weighted accumulation, neighbor index offsets | Constant 5, linear [-1,-2,-3,-4], adjacent pairs (0,1), (1,2), (2,3), each coefficient 2 |
| [exactly_one.py](exactly_one.py) | Squared selection-count penalty built from a loop and locals | Constant 10, linear [-11,-12,-13], all three pairs coefficient 20 |

For `minimize_three_bits.py`, assignments `000`, `001`, `100`, and `101` have
objectives 5, 5, 3, and 6 respectively. For maximization, `011` has canonical value
-6 and original value 6. API bitstrings put x[0] first and preserve leading zeros.
For the bounded-loop example, `0000`, `1000`, `1111`, and `0101` have objectives
5, 4, 1, and -1. These are arithmetic reference values, not sampled QAOA outputs.

The exactly-one example minimizes `10*(selected-1)**2 - benefit`. Reference values
for all eight inputs, checked independently of extraction:

| Assignment | Objective |
| --- | --- |
| 000 | 10 |
| 001 | -3 |
| 010 | -2 |
| 011 | 5 |
| 100 | -1 |
| 101 | 6 |
| 110 | 7 |
| 111 | 34 |

The mathematical minimum for this tiny example is -3 at `001`, selecting x[2].
The penalty weight 10 is supplied by the source; the compiler does not select weights
or return a separate constraint-feasibility result.

The benchmark endpoint still depends on Developer 3's shared runner stubs; these
examples do not submit jobs or provide mock production measurements. See
[the compiler guide](../../docs/COMPILER.md) for the supported subset and limits.
