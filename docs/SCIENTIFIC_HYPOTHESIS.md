# Q-Atlas: a reusable platform for quantum experimentation

**Our goal:** We wanted to create one place to benchmark common quantum computing
questions and provide a boilerplate Python-to-Qiskit compiler for exploring new
optimization problems. Q-Atlas brings problem formulation, circuit generation,
classical comparisons, and result interpretation into a shared workflow.

**Research question:** Can reusable benchmarking tools and automated translation
of supported Python objectives reduce the effort needed to investigate a new
problem while preserving correctness and meaningful classical comparisons?

**Hypothesis:** For supported problems, Q-Atlas will require less problem-specific
setup code than building each Qiskit experiment independently, while preserving
the mathematical objective and producing reproducible comparisons of accuracy,
solution quality, and computational resources.

## What does the app investigate?

| Experience | Question and comparison |
| --- | --- |
| Materials | How accurately do quantum circuits reproduce spin dynamics compared with independent classical evolution? |
| Neutrinos | How do matter conditions affect flavor-conversion probabilities in an effective two-flavor model? Compare circuits with analytical and numerical references. |
| Optimization | How close does QAOA get to the best solution of a binary optimization problem compared with classical solvers? |
| Search | How does Grover success probability change with iteration count, and how do its query requirements compare with classical search? |
| Python compiler | Can a new supported objective be translated into a QUBO and Qiskit circuit without manually rebuilding the quantum workflow? |

Each experiment retains its own model, assumptions, and success criteria. The
compiler supports a restricted class of binary quadratic objectives; it generates
Qiskit scaffolding and connects to the shared QAOA implementation. This gives new
optimization problems a starting point within the same experimental framework.

## How would we test the hypothesis?

Use the same small problems in Q-Atlas and independently written Qiskit workflows:

- **Setup effort:** Measure problem-specific code and time needed to reach the
  first validated comparison under matched tasks and developer experience.
- **Correctness:** Check compiled objectives against their source formulation on
  every binary assignment for small instances. Validate physical observables and
  search probabilities against independent references.
- **Benchmark quality:** Record solution quality or observable error alongside
  runtime, qubits, circuit depth, shots, and optimizer settings where applicable.
  Repeat stochastic runs with recorded seeds and retain raw results.

The hypothesis is weakened if setup effort does not decrease, translation changes
the objective, or comparisons cannot be reproduced within their stated uncertainty.
The reduction in setup effort remains **unmeasured**.

## Why does this matter, and what is creative about it?

**Depth of understanding:** A useful comparison must solve the same mathematical
problem on both paths. Query complexity, simulator runtime, and physical QPU usage
answer different questions; accuracy and solution quality must accompany timing.

**Potential impact:** Researchers and students could spend less time assembling
experiment infrastructure and more time testing models, exploring parameters, and
deciding whether a quantum approach merits further investigation. Larger studies
would require stronger classical baselines and explicit hardware-error analysis.

**Creativity:** Our contribution is the connection between established quantum
experiments and an extensible compiler workflow. Users can explore familiar
benchmarks, then introduce their own supported objectives using the same approach
to validation and comparison. The algorithms themselves are established methods.

Q-Atlas's existing evidence includes local simulator results; these do not establish
quantum advantage or validate the platform-wide hypothesis. See the
[scientific report](PROJECT_SCIENTIFIC_REPORT.md) for model formulations, algorithm
citations, recorded results, and reproduction inputs, and the
[compiler guide](COMPILER.md) for supported syntax.
