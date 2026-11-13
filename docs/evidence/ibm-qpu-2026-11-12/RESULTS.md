# Five Q-Atlas experiments on a physical IBM QPU

Device: **ibm_marrakesh**. Job: **dbr0sthabdes73fp2v60**. Status: **DONE**.

[IBM workload](https://quantum.cloud.ibm.com/workloads/dbr0sthabdes73fp2v60) · [Raw evidence](five-experiments.json) · [Source provenance](provenance.json)

This is a real hardware run, `simulated: false`, containing eight circuits and 1024 total samples (128 per circuit). The five experiments share one job and one 10-second maximum-execution reservation. IBM reported **2.0 seconds of usage for the entire job**. Child results must not be assigned this entire usage individually.

| Experiment / quantity | Coordinate | Classical reference | Physical QPU | Absolute error / gap |
| --- | ---: | ---: | ---: | ---: |
| compiler: Objective (minimize) | — | 3 | 3 | 0 |
| optimization: Objective (minimize) | — | -2 | -2 | 0 |
| search: Marked-state success probability | — | 1 | 0.8515625 | 0.1484375 |
| materials: magnetization_z | 1 | 0.403062466 | 0.46875 | 0.0656875343 |
| materials: energy | 1 | -1 | -1.021875 | 0.021875 |
| neutrinos: electron flavor probability | 0 | 0.908117318 | 0.8828125 | 0.0253048179 |
| neutrinos: other flavor probability | 0 | 0.0918826821 | 0.1171875 | 0.0253048179 |
| neutrinos: electron flavor probability | 0.921060994 | 0 | 0.015625 | 0.015625 |
| neutrinos: other flavor probability | 0.921060994 | 1 | 0.984375 | 0.015625 |
| neutrinos: electron flavor probability | 1.84212199 | 0.908117318 | 0.8828125 | 0.0253048179 |
| neutrinos: other flavor probability | 1.84212199 | 0.0918826821 | 0.1171875 | 0.0253048179 |

Compiler and Optimization sampled their exact optima. Search succeeded in 109/128 shots (85.15625%); its ideal circuit prediction is 94.53125%, while the completed classical search succeeds with probability one. The noisy QPU success is a measurement, not a promised success rate. Neutrino conversion at resonance was 126/128 (98.4375%). Materials results include Trotter, shot and device error.

Classical reference time across all five: 8.6901 ms. Local angle training: 1449.29 ms. Preparation contains those intervals. Transpilation: 53.7986 ms. Submission: 576.632 ms. Retrieval: 145.466 ms.

Provider timestamp intervals: created-to-running 1057.42 ms; running-to-finished 4218.87 ms. Observed wall time was 96003.3 ms and includes delayed polling. RUNNING includes provider classical work and contention; it is not pure QPU execution time.

This establishes that all five circuits ran on hardware. It establishes no practical quantum speedup. Classical and quantum paths have different work and measurement costs, and these are tiny teaching instances.

[IBM timing guidance](https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/monitor-job) explains why provider RUNNING duration and QPU usage differ.
