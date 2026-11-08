<script lang="ts">
  import Icon from '#lib/components/Icon.svelte';
</script>

<svelte:head><title>Methodology · Q-Atlas</title></svelte:head>

<header class="page-heading">
  <div>
    <h1>Methodology</h1>
    <p>The scientific scope and validation plan for the Neutrino Lab.</p>
  </div>
</header>

<article class="methodology">
  <section>
    <h2>Physical model</h2>
    <p>
      The lab targets single-neutrino flavor propagation in vacuum and constant-density matter. The
      scientific backend must declare which models, initial states, and output flavors it
      implements. Two- or three-flavor support is not assumed.
    </p>
    <p>
      Vacuum propagation excludes a matter potential. Constant-density matter adds a
      forward-scattering potential with uniform density and composition. Variable-density,
      interacting-neutrino, and supernova models are outside the current scope.
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
      The neutrino API and model capabilities are awaiting team agreement. Configuration and
      execution are disabled. No neutrino results, example dataset, or frontend physics calculation
      is included.
    </p>
    <a class="text-link" href="/neutrinos/">Open Neutrino Lab<Icon name="arrow" size={14} /></a>
  </section>
</article>

<style>
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
