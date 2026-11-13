<script lang="ts">
  import Icon from '#lib/components/Icon.svelte';
</script>

<svelte:head><title>Overview · Q-Atlas</title></svelte:head>

<div class="overview">
  <header class="introduction">
    <h1>Q-Atlas</h1>
    <p>Neutrino oscillations with independent classical and quantum calculations.</p>
    <p class="challenge">Ohio State Qiskit Fall Fest 2026 · Quantum for Science</p>
  </header>

  <section class="lab-entry" aria-labelledby="lab-title">
    <div class="lab-introduction">
      <h2 id="lab-title">Neutrino Lab</h2>
      <p>
        Explore how neutrino flavor changes in vacuum and matter. Compare Qiskit calculations with
        an independent SciPy reference, study sampling error across shots and seeds, and inspect
        recorded IBM hardware measurements.
      </p>
      <div class="workspace-actions">
        <a class="button primary" href="/neutrinos/">
          Launch Neutrino Lab<Icon name="arrow" size={17} />
        </a>
        <a class="text-link" href="/methodology/">Methodology and science report</a>
      </div>
    </div>
    <dl class="capabilities" aria-label="Implemented simulation capabilities">
      <div>
        <dt>Model</dt>
        <dd>Two flavors · electron and effective other</dd>
      </div>
      <div>
        <dt>Environments</dt>
        <dd>Vacuum, constant-density matter and two layers</dd>
      </div>
      <div>
        <dt>Execution</dt>
        <dd>Local Aer simulation and physical IBM measurements</dd>
      </div>
    </dl>
  </section>

  <div class="supporting">
    <section class="science" aria-labelledby="science-title">
      <h2 id="science-title">Why neutrino oscillations?</h2>
      <p>
        A neutrino prepared in one flavor can be detected in another after propagation. Its mass
        states accumulate different phases, changing the flavor probabilities. Matter changes this
        evolution. The lab uses an effective two-flavor model to study these effects.
      </p>
    </section>

    <section class="compiler" aria-labelledby="compiler-title">
      <h2 id="compiler-title">Python Compiler</h2>
      <p>
        Convert supported Python optimization objectives into QUBO representations and Qiskit
        circuits. Compare classical and shared QAOA solvers, with local and physical IBM execution.
      </p>
      <a class="button" href="/compiler/">Open Python Compiler<Icon name="arrow" size={16} /></a>
    </section>
  </div>
  <div class="hardware-reference">
    <a class="text-link" href="/hardware/"
      >View recorded IBM hardware results<Icon name="arrow" size={14} /></a
    >
  </div>
</div>

<style>
  .overview {
    max-width: 1120px;
    margin: 0 auto;
  }
  .introduction {
    padding: 4px 0 30px;
  }
  h1 {
    font-size: 36px;
    font-weight: 500;
    letter-spacing: -0.045em;
    line-height: 1.2;
    margin: 0 0 9px;
  }
  .introduction p {
    margin: 0;
    font-size: 17px;
    color: var(--muted);
  }
  .introduction .challenge {
    margin-top: 10px;
    font-size: 13px;
  }
  .lab-entry {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    gap: 36px;
    padding: 32px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 3px solid var(--blue);
    border-radius: 3px;
  }
  h2 {
    font-size: 17px;
    font-weight: 500;
    margin: 0 0 12px;
  }
  .lab-introduction h2 {
    font-size: 26px;
    letter-spacing: -0.035em;
  }
  .lab-introduction p,
  .science p,
  .compiler p {
    font-size: 14px;
    line-height: 1.8;
    color: var(--muted);
    margin: 0;
    max-width: 60ch;
  }
  .workspace-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
    margin-top: 26px;
  }
  .workspace-actions .button {
    min-height: 44px;
  }
  .capabilities {
    margin: 0;
    border-left: 1px solid var(--border);
    padding-left: 30px;
    display: grid;
    gap: 21px;
    align-content: center;
  }
  dt {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 5px;
  }
  dd {
    font-size: 13px;
    line-height: 1.6;
    margin: 0;
  }
  .supporting {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    gap: 64px;
    margin-top: 36px;
  }
  .compiler .button {
    margin-top: 20px;
  }
  .hardware-reference {
    border-top: 1px solid var(--border);
    margin-top: 32px;
    padding-top: 20px;
  }
  @media (max-width: 800px) {
    .lab-entry,
    .supporting {
      grid-template-columns: 1fr;
      gap: 28px;
    }
    .capabilities {
      border-left: 0;
      border-top: 1px solid var(--border);
      padding: 24px 0 0;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 20px;
    }
  }
  @media (max-width: 500px) {
    .introduction {
      padding-bottom: 24px;
    }
    .lab-entry {
      padding: 24px;
    }
    .capabilities {
      grid-template-columns: 1fr;
      gap: 16px;
    }
  }
</style>
