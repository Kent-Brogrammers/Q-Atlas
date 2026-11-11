<script lang="ts">
  import Icon from '#lib/components/Icon.svelte';
</script>

<svelte:head><title>Overview · Q-Atlas</title></svelte:head>

<div class="overview">
  <header class="introduction">
    <h1>Q-Atlas</h1>
    <p>
      Convert marked Python objectives into circuit code, or explore the Neutrino Lab. Each
      workspace shows its validation and execution status.
    </p>
    <div class="workspace-actions">
      <a class="button primary workspace-action-button" href="/compiler/">
        <span class="button-text">Open Python Compiler</span>
        <span class="button-icon"><Icon name="arrow" size={30} /></span>
      </a>
      <a class="button primary workspace-action-button" href="/neutrinos/">
        <span class="button-text">Launch Neutrino Lab</span>
        <span class="button-icon"><Icon name="arrow" size={30} /></span>
      </a>
      <a class="button primary workspace-action-button" href="/search/">
        <span class="button-text">Explore Grover Search</span>
        <span class="button-icon"><Icon name="arrow" size={30} /></span>
      </a>
    </div>
  </header>

  <section class="compiler" aria-labelledby="compiler-title">
    <h2 id="compiler-title">Python compiler</h2>
    <p>
      Load a .py file, mark one supported binary objective with <code>@qatlas.objective</code>, and
      download the converted script. Your function names, input names, and surrounding Python stay
      in place. No circuit code is required.
    </p>
    <p>
      Source conversion and comparison planning are available. Quantum execution stays disabled.
    </p>
  </section>

  <section class="science" aria-labelledby="science-title">
    <h2 id="science-title">Why neutrino oscillations?</h2>
    <p>
      A neutrino prepared in one flavor can be detected in another after propagation. This arises
      from mixing between flavor and mass states; matter can also change its evolution.
    </p>
    <p>
      Q-Atlas aims to compare flavor probabilities from a quantum circuit with an independent
      classical reference, measuring how closely they agree.
    </p>
    <a class="text-link" href="/methodology/">Read the methodology<Icon name="arrow" size={14} /></a
    >
  </section>

  <section class="capabilities" aria-labelledby="capabilities-title">
    <h2 id="capabilities-title">Simulation availability</h2>
    <dl>
      <div>
        <dt>Neutrino models and flavors</dt>
        <dd>Effective two-flavor model · electron and other flavor</dd>
      </div>
      <div>
        <dt>Vacuum and constant-density matter</dt>
        <dd>Available, including two-layer profiles</dd>
      </div>
      <div>
        <dt>Classical–Qiskit comparison</dt>
        <dd>SciPy reference, ideal Aer, and finite-shot measurements</dd>
      </div>
    </dl>
    <p>
      Choose an experiment in the Neutrino Lab to explore its flavor probabilities.
    </p>
  </section>
</div>

<style>
  .overview {
    max-width: 980px;
  }
  .introduction {
    padding: 14px 0 32px;
  }
  h1 {
    font-size: 38px;
    font-weight: 400;
    line-height: 1.2;
    margin: 0 0 14px;
  }
  .introduction p {
    max-width: 650px;
    margin: 0 0 24px;
    font-size: 19px;
    line-height: 1.55;
    color: var(--muted);
  }
  .introduction .workspace-action-button {
    min-width: 215px;
    min-height: 0;
    justify-content: center;
    gap: 8px;
    padding: 12px 20px;
    border: 6px solid #88add3;
    border-radius: 50px;
    background: #12345b;
    color: #fff;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 1px;
    transition:
      background-color 0.3s,
      border-color 0.3s,
      border-width 0.15s;
  }
  .introduction .workspace-action-button:hover {
    border-color: #6e9bc9;
    background: #194a79;
  }
  .introduction .workspace-action-button:active {
    border-width: 5px;
  }
  .introduction .workspace-action-button:focus-visible {
    outline-color: var(--text);
  }
  .button-text {
    font-size: 1.4em;
    line-height: 1.15;
  }
  .button-icon {
    display: inline-flex;
    align-items: center;
    padding-top: 5px;
  }
  .button-icon :global(svg) {
    width: 24px;
    height: 24px;
  }
  .workspace-action-button:hover .button-icon :global(svg) {
    animation: jello-vertical 0.9s both;
    transform-origin: left;
  }
  @keyframes jello-vertical {
    0% {
      transform: scale3d(1, 1, 1);
    }
    30% {
      transform: scale3d(0.75, 1.25, 1);
    }
    40% {
      transform: scale3d(1.25, 0.75, 1);
    }
    50% {
      transform: scale3d(0.85, 1.15, 1);
    }
    65% {
      transform: scale3d(1.05, 0.95, 1);
    }
    75% {
      transform: scale3d(0.95, 1.05, 1);
    }
    100% {
      transform: scale3d(1, 1, 1);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .introduction .workspace-action-button {
      transition: none;
    }
    .workspace-action-button:hover .button-icon :global(svg) {
      animation: none;
    }
  }
  .workspace-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  section {
    border-top: 1px solid var(--border);
    padding: 26px 0;
  }
  h2 {
    margin: 0 0 14px;
    font-size: 18px;
    font-weight: 500;
  }
  .science p,
  .compiler p {
    max-width: 720px;
    margin: 0 0 12px;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.75;
  }
  .science .text-link {
    margin-top: 4px;
  }
  dl {
    margin: 0;
  }
  dl > div {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 16px;
    padding: 13px 0;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
  }
  dt {
    color: var(--text);
  }
  dd {
    margin: 0;
    color: var(--muted);
  }
  .capabilities > p {
    margin: 16px 0 0;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
  }
  @media (max-width: 650px) {
    .introduction {
      padding-top: 4px;
    }
    .introduction .workspace-action-button {
      width: 100%;
      min-width: 0;
    }
    h1 {
      font-size: 32px;
    }
    .introduction p {
      font-size: 17px;
    }
    dl > div {
      grid-template-columns: 1fr;
      gap: 5px;
    }
  }
</style>
