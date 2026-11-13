<script lang="ts">
  import Icon from '#lib/components/Icon.svelte';
  import qpuEvidence from '../../../../docs/evidence/ibm-qpu-2026-11-12/five-experiments.json?url';
  import qpuReport from '../../../../docs/evidence/ibm-qpu-2026-11-12/RESULTS.md?url';
  import finalReport from '../../../../docs/FINAL_SCIENCE_REPORT.md?url';
  import finalFigure from '../../../../docs/evidence/ibm-qpu-2026-11-12/final-results.png?url';
  import scienceAnswers from '../../../../docs/SCIENCE_CHALLENGE_ANSWERS.md?url';
  import evidenceFigure from '../../../../docs/evidence/fall-fest-2026-11-12/neutrino-resonance.png?url';
  import evidenceRaw from '../../../../docs/evidence/fall-fest-2026-11-12/neutrino-resonance.json?url';
  import evidenceProvenance from '../../../../docs/evidence/fall-fest-2026-11-12/provenance.json?url';
</script>

<svelte:head><title>Methodology · Q-Atlas</title></svelte:head>

<header class="page-heading">
  <div>
    <h1>Methodology</h1>
    <p>
      Neutrino oscillations for Quantum for Science, with a supporting Python optimization compiler.
    </p>
  </div>
</header>

<article class="methodology">
  <section>
    <h2>Our scientific question</h2>
    <p>
      How does matter change neutrino flavor conversion, and how accurately does a one-qubit circuit
      reproduce an independent prediction with finite measurements?
    </p>
    <p>
      We compare the same normalized model and inputs using independent SciPy calculations and
      Qiskit circuits. Repeated experiments vary shot counts and seeds to measure sampling error.
      Recorded IBM hardware measurements provide a physical comparison alongside local Aer results.
    </p>
    <p>
      <a class="text-link" href={scienceAnswers} download="Q-Atlas-science-challenge-answers.md"
        >Download the science challenge answers</a
      >
    </p>
    <figure>
      <img
        src={evidenceFigure}
        alt="Previously measured local Aer neutrino conversion curve and sampling errors across shot counts"
      />
      <figcaption>
        Previously measured local Aer results · November 12, 2026 · 81 point records. Ranges are
        observed min–max across three seeds, not confidence intervals.
      </figcaption>
    </figure>
    <p>
      <a href={evidenceRaw} download="neutrino-resonance.json">Download raw evidence</a> ·
      <a href={evidenceProvenance} download="provenance.json">Source provenance</a>
    </p>
  </section>
  <section>
    <h2>Supporting Python Compiler</h2>
    <p>
      The compiler translates supported Python binary optimization objectives into QUBO
      representations and Qiskit circuits. It compares classical optimization with the shared QAOA
      solver, using local simulation or supported physical IBM execution.
    </p>
    <a class="text-link" href="/compiler/">Open Python Compiler<Icon name="arrow" size={14} /></a>
  </section>
  <section>
    <h2>Final science report and presentation material</h2>
    <p>
      The final report follows the challenge's problem, model, mapping, method, baseline, results,
      scaling and impact questions. It distinguishes actual physical measurements from ideal
      simulation and theoretical resource claims.
    </p>
    <p>
      <a class="text-link" href={finalReport} download="Q-Atlas-final-science-report.md"
        >Download final science report</a
      >
      · <a href="/q-atlas-presentation.zip" download>Download presentation pack</a>
    </p>
    <details class="supplementary">
      <summary>Full hardware results figure for all five experiments</summary>
      <figure>
        <a href={finalFigure} download="Q-Atlas-final-results.png"
          ><img
            src={finalFigure}
            alt="Final Q-Atlas physical results for search, neutrinos, materials and optimization, with conditional shot uncertainty"
          /></a
        >
        <figcaption>
          Recorded physical QPU data. Intervals describe conditional shot uncertainty and exclude
          device bias, drift and model error. Click the figure to download it.
        </figcaption>
      </figure>
    </details>
  </section>

  <section>
    <h2>Physical model</h2>
    <p>
      The lab implements effective two-flavor propagation from an initial electron neutrino. One
      simulated qubit encodes electron flavor and one effective other active flavor. Inputs use
      normalized units, with the mixing angle in radians.
    </p>
    <p>
      Vacuum propagation excludes a matter potential. Constant-density matter adds a
      forward-scattering potential with uniform density and composition. Ordered piecewise-constant
      layers are supported. Smooth profiles, interacting-neutrino, three-flavor, and realistic
      supernova models are outside the current scope.
    </p>
    <a
      class="text-link"
      href="https://pdg.lbl.gov/2025/reviews/rpp2025-rev-neutrino-mixing.pdf"
      target="_blank"
      rel="noreferrer"
      >Physical background: PDG neutrino review<Icon name="northeast" size={14} /></a
    >
  </section>
  <section>
    <h2>Independent classical comparison</h2>
    <p>
      Classical and Qiskit calculations must use the same physical inputs and propagation grid. The
      classical reference must be independent of the circuit construction. Mixing parameters, mass
      differences, units, state encoding, and parameter sources belong in the returned record.
    </p>
    <p>
      Validation should include zero propagation distance, probability conservation in the modeled
      space, and the vacuum limit of the matter model. The backend must report absolute probability
      errors, their aggregation, and the tolerance used to assess accuracy.
    </p>
  </section>
  <section>
    <h2>Execution and uncertainty</h2>
    <p>
      Statevector probabilities and finite-shot estimates must be identified separately. Missing
      measurements remain unavailable; a measured zero stays zero. Shot uncertainty and model
      approximation error need distinct explanations.
    </p>
    <p>
      Report the simulator, package versions, seed, qubits, circuit-depth scope, actual shots, and
      timing scope. Simulator accuracy does not establish hardware performance or quantum advantage.
    </p>
  </section>
  <section>
    <h2>Current availability</h2>
    <p>
      Vacuum, constant matter, two-layer profiles, and density sweeps run through the neutrino API.
      The backend computes analytical predictions where applicable, an independent SciPy reference,
      ideal Aer statevectors, and finite-shot measurements. The browser plots those returned
      records.
    </p>
    <a class="text-link" href="/neutrinos/">Open Neutrino Lab<Icon name="arrow" size={14} /></a>
  </section>
  <details class="archive">
    <summary>Original five-experiment IBM hardware record</summary>
    <section>
      <h2>All five experiments executed on IBM hardware</h2>
      <p>
        Physical IBM device: ibm_marrakesh. Completed job: dbr0sthabdes73fp2v60. Eight circuits
        covered Compiler, Optimization, Grover Search, Materials and Neutrinos, with 128 shots per
        circuit. Provider usage was 2.0 seconds for the entire shared job.
      </p>
      <p>
        Compiler and Optimization sampled their exact optima. Search succeeded in 109 of 128 shots;
        neutrino conversion at the resonant point was 126 of 128. The app compares each measurement
        with its independent classical reference. Per-experiment QPU runtime is unavailable because
        the experiments shared a job.
      </p>
      <p>
        <a href="/hardware/">Open physical QPU analytics</a> ·
        <a href={qpuEvidence} download="q-atlas-five-physical-qpu.json"
          >Download raw hardware evidence</a
        >
        · <a href={qpuReport} download="Q-Atlas-physical-results.md">Download results report</a>
      </p>
      <p>
        Supporting experiments compare the same model and input on both paths. Observable error or
        solution quality accompanies runtime. Grover demonstrates theoretical oracle-query
        improvement. Local simulator runtime and physical QPU usage are different measurements. The
        project has established no practical quantum speedup.
      </p>
    </section>
  </details>
</article>

<style>
  summary {
    cursor: pointer;
    line-height: 1.6;
  }
  .supplementary {
    margin-top: 20px;
    font-size: 13px;
  }
  .archive {
    border-top: 1px solid var(--border);
    padding: 24px 0;
  }
  .archive > summary {
    font-size: 17px;
    font-weight: 500;
  }
  .archive > section {
    border: 0;
    padding-bottom: 0;
  }
  figure {
    margin: 20px 0;
  }
  img {
    width: 100%;
    height: auto;
  }
  figcaption {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.7;
  }
  .methodology {
    max-width: 820px;
  }
  section {
    padding: 24px 0;
    border-top: 1px solid var(--border);
  }
  h2 {
    margin: 0 0 12px;
    font-size: 18px;
    font-weight: 500;
  }
  p {
    margin: 0 0 12px;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.75;
  }
  section p:last-child {
    margin-bottom: 0;
  }
</style>
