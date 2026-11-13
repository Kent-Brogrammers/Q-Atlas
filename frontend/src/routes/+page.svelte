<script lang="ts">
  import Icon from '#lib/components/Icon.svelte';
</script>

<svelte:head><title>Overview · Q-Atlas</title></svelte:head>

<div class="overview">
  <header class="introduction">
    <h1>Q-Atlas</h1>
    <p>Neutrino simulation and classical validation.</p>
  </header>

  <section class="lab-entry" aria-labelledby="lab-title">
    <div class="lab-introduction">
      <h2 id="lab-title">Neutrino Lab</h2>
      <p>
        Explore how neutrino flavor changes with distance and matter. Compare Qiskit Aer
        probabilities and finite-shot measurements with an independent SciPy reference.
      </p>
      <div class="workspace-actions">
        <a class="button primary" href="/neutrinos/">
          Launch Neutrino Lab<Icon name="arrow" size={17} />
        </a>
        <a class="text-link" href="/methodology/">Read the methodology</a>
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
        <dd>Local Aer simulation · normalized units</dd>
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

    <section class="workspaces" aria-labelledby="workspaces-title">
      <h2 id="workspaces-title">Other workspaces</h2>
      <a href="/compiler/">
        <span
          >Python Compiler<small>Convert supported binary objectives into circuit code</small></span
        ><Icon name="arrow" size={16} />
      </a>
      <a href="/search/">
        <span
          >Grover Search<small>Explore amplitude amplification and search probabilities</small
          ></span
        ><Icon name="arrow" size={16} />
      </a>
    </section>
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
  .science p {
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
  .workspaces a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
  }
  .workspaces a:first-of-type {
    padding-top: 0;
  }
  .workspaces a:hover {
    color: var(--blue);
  }
  .workspaces small {
    display: block;
    margin-top: 5px;
    font-size: 12px;
    line-height: 1.6;
    color: var(--muted);
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
