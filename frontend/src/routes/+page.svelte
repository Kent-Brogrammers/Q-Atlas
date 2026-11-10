<script lang="ts">
  import Icon from '#lib/components/Icon.svelte';
</script>

<svelte:head><title>Overview · Q-Atlas</title></svelte:head>

<div class="overview">
  <header class="introduction">
    <h1>Q-Atlas</h1>
    <p>
      Neutrino oscillation simulation with Qiskit, compared against independent classical
      calculations.
    </p>
    <a class="button primary" href="/neutrinos/"
      >Launch Neutrino Lab<Icon name="arrow" size={18} /></a
    >
  </header>

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
        <dd>Awaiting backend definition</dd>
      </div>
      <div>
        <dt>Vacuum and constant-density matter</dt>
        <dd>Planned · support unconfirmed</dd>
      </div>
      <div>
        <dt>Classical–Qiskit comparison</dt>
        <dd>Not connected</dd>
      </div>
    </dl>
    <p>No neutrino experiments can run yet. The Lab shows configuration and result requirements.</p>
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
    color: #45536a;
  }
  .introduction .button {
    min-width: 230px;
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
  .science p {
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
    color: #344158;
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
