<script lang="ts">
  import { onDestroy } from 'svelte';
  import Panel from '#lib/components/Panel.svelte';
  import NeutrinoProbabilityChart from '#lib/components/NeutrinoProbabilityChart.svelte';
  import { api, ApiError } from '../../api/client.ts';
  import type { NeutrinoResponse } from '../../types/index.ts';
  import { buildRequest, defaultSettings, flavorChannels } from '#lib/neutrinos/live.ts';
  import { formatValue } from '#lib/neutrinos/presentation.ts';

  let settings = $state(defaultSettings());
  let result = $state<NeutrinoResponse | null>(null);
  let loading = $state(false);
  let error = $state('');
  let selectedIndex = $state(0);
  let controller: AbortController | undefined;
  let selected = $derived(result?.results[selectedIndex]);
  onDestroy(() => controller?.abort());

  function clearResult() {
    result = null;
    error = '';
  }
  function preset(kind: 'vacuum' | 'resonance' | 'layers') {
    clearResult();
    settings = defaultSettings();
    if (kind === 'resonance') {
      settings.environment = 'density';
      // Published normalized example from docs/NEUTRINOS.md, not simulated results.
      settings.distance = 4.0336988686318564;
    } else if (kind === 'layers') {
      settings.environment = 'layers';
      settings.potential = 0.2;
      settings.distance = 2;
    }
  }
  async function runExperiment(event: SubmitEvent) {
    event.preventDefault();
    if (loading) return;
    clearResult();
    try {
      const request = buildRequest(settings);
      loading = true;
      controller = new AbortController();
      result = await api.neutrinos(request, controller.signal);
      selectedIndex =
        result.axis === 'potential'
          ? Math.floor(result.results.length / 2)
          : result.results.length - 1;
    } catch (cause) {
      error =
        cause instanceof ApiError
          ? [
              cause.message,
              ...(cause.body.error.diagnostics ?? []).map((item) => item.message)
            ].join(' ')
          : cause instanceof Error
            ? cause.message
            : 'The experiment failed. Please try again.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head
  ><title>Neutrino Lab · Q-Atlas</title><meta
    name="description"
    content="Run two-flavor neutrino propagation and compare SciPy, Qiskit statevectors, and finite-shot measurements."
  /></svelte:head
>
<header class="page-heading">
  <div>
    <h1>Neutrino Lab</h1>
    <p>Explore how matter changes flavor oscillations with a one-qubit simulation.</p>
  </div>
</header>
<p class="notice">
  Effective two-flavor model · initial electron flavor · Qiskit Aer simulator. Angle is in radians;
  energy, mass splitting, distance, and potential use normalized units.
</p>
<div class="presets" aria-label="Example configurations">
  <span>Load example:</span>
  <button class="button" disabled={loading} onclick={() => preset('vacuum')}>Vacuum</button>
  <button class="button" disabled={loading} onclick={() => preset('resonance')}
    >MSW resonance</button
  >
  <button class="button" disabled={loading} onclick={() => preset('layers')}>Two layers</button>
</div>
{#if error}<div class="error" role="alert">
    <strong>Experiment could not run.</strong>
    {error}
    <p>Check that the Q-Atlas backend is running at http://127.0.0.1:8000.</p>
  </div>{/if}
<div class="lab-layout">
  <aside aria-label="Experiment configuration">
    <Panel title="Configuration" subtitle="Effective two-flavor propagation">
      <form onsubmit={runExperiment} oninput={clearResult}>
        <fieldset disabled={loading}>
          <legend>Propagation</legend>
          <label for="environment">Environment</label>
          <select id="environment" bind:value={settings.environment}>
            <option value="vacuum">Vacuum</option><option value="matter"
              >Constant-density matter</option
            ><option value="layers">Two equal-length layers</option><option value="density"
              >Matter density sweep</option
            >
          </select>
          <label for="particle">Particle</label><select id="particle" bind:value={settings.particle}
            ><option value="neutrino">Neutrino</option><option value="antineutrino"
              >Antineutrino</option
            ></select
          >
          <label for="theta">Mixing angle (radians)</label><input
            id="theta"
            type="number"
            min="0"
            max={Math.PI / 2}
            step="any"
            required
            bind:value={settings.theta}
          />
          <label for="delta">Mass-squared splitting (normalized)</label><input
            id="delta"
            type="number"
            min="-10"
            max="10"
            step="any"
            required
            bind:value={settings.delta_m2}
          />
          <label for="energy">Energy (normalized)</label><input
            id="energy"
            type="number"
            min="0.01"
            max="100"
            step="any"
            required
            bind:value={settings.energy}
          />
          <label for="distance">Total distance (normalized)</label><input
            id="distance"
            type="number"
            min="0"
            max="100"
            step="any"
            required
            bind:value={settings.distance}
          />
          {#if settings.environment === 'matter' || settings.environment === 'layers'}
            <label for="potential"
              >{settings.environment === 'layers' ? 'First layer potential' : 'Matter potential'} (normalized)</label
            ><input
              id="potential"
              type="number"
              min="0"
              max="10"
              step="any"
              required
              bind:value={settings.potential}
            />
          {/if}
          {#if settings.environment === 'layers'}
            <label for="second-potential">Second layer potential (normalized)</label><input
              id="second-potential"
              type="number"
              min="0"
              max="10"
              step="any"
              required
              bind:value={settings.second_potential}
            />
          {/if}
          {#if settings.environment === 'density'}
            <label for="max-potential">Maximum potential (normalized)</label><input
              id="max-potential"
              type="number"
              min="0"
              max="10"
              step="any"
              required
              bind:value={settings.max_potential}
            />
            <p class="hint">Sweep from zero to this potential at the fixed total distance.</p>
          {/if}
          <legend>Sampling</legend>
          <label for="samples">Curve points</label><input
            id="samples"
            type="number"
            min="2"
            max="41"
            step="1"
            required
            bind:value={settings.samples}
          />
          <label for="shots">Shots per point</label><input
            id="shots"
            type="number"
            min="1"
            max="100000"
            step="1"
            required
            bind:value={settings.shots}
          />
          <label for="seed">Initial simulator seed</label><input
            id="seed"
            type="number"
            min="0"
            max="4294967295"
            step="1"
            required
            bind:value={settings.seed}
          />
          <p class="hint">
            Curve points × shots must be at most 500,000. Seeds increment at each point.
          </p>
          <button class="button primary" type="submit"
            >{loading ? 'Running experiment…' : 'Run experiment'}</button
          >
        </fieldset>
      </form>
    </Panel>
  </aside>
  <div class="results" aria-busy={loading}>
    <p role="status" class="status">
      {loading
        ? 'Calculating classical references and sampling Qiskit Aer…'
        : result
          ? `Completed ${result.results.length} points · all results are simulated.`
          : 'Choose a configuration and run the experiment.'}
    </p>
    <Panel
      title="Flavor probabilities"
      subtitle="Independent reference, ideal circuit, and finite shots"
      ><NeutrinoProbabilityChart {result} /></Panel
    >
    <Panel title="Comparison & run details" subtitle="Inspect a measured point">
      <div class="details">
        {#if result && selected}
          <label for="point"
            >{result.axis === 'potential' ? 'Matter potential' : 'Propagation distance'} (normalized)</label
          >
          <select id="point" bind:value={selectedIndex}
            >{#each result.coordinates as coordinate, index}<option value={index}
                >{formatValue(coordinate)}</option
              >{/each}</select
          >
          <div class="table-scroll">
            <table>
              <caption>Flavor probabilities at the selected point</caption>
              <thead
                ><tr
                  ><th>Flavor</th><th>Analytical</th><th>SciPy</th><th>Ideal</th><th>Shots</th></tr
                ></thead
              >
              <tbody
                >{#each flavorChannels as flavor}<tr
                    ><th>{flavor.label}</th><td>{formatValue(selected.analytical?.[flavor.key])}</td
                    ><td>{formatValue(selected.numerical[flavor.key])}</td><td
                      >{formatValue(selected.ideal[flavor.key])}</td
                    ><td>{formatValue(selected.measured[flavor.key])}</td></tr
                  >{/each}</tbody
              >
            </table>
          </div>
          <dl>
            <div>
              <dt>Mixing strength sin²(2θm)</dt>
              <dd>{formatValue(selected.analytical?.mixing_strength)}</dd>
            </div>
            <div>
              <dt>Effective mixing angle (radians)</dt>
              <dd>{formatValue(selected.analytical?.theta_m)}</dd>
            </div>
            <div>
              <dt>Ideal vs SciPy conversion error</dt>
              <dd>{formatValue(selected.absolute_errors.ideal_vs_numerical.other)}</dd>
            </div>
            <div>
              <dt>Shot sampling conversion error</dt>
              <dd>{formatValue(selected.absolute_errors.sampling.other)}</dd>
            </div>
            <div>
              <dt>Subdivision state change</dt>
              <dd>{formatValue(selected.numerics.subdivision_check.state_change_l2)}</dd>
            </div>
            <div>
              <dt>Qubits / depth (with measurement)</dt>
              <dd>{selected.num_qubits} / {selected.circuit_depth}</dd>
            </div>
            <div>
              <dt>Shots / seed</dt>
              <dd>{selected.shots} / {selected.configuration.seed}</dd>
            </div>
            <div>
              <dt>Classical reference (ms)</dt>
              <dd>{formatValue(selected.timing_ms.classical, 3)}</dd>
            </div>
            <div>
              <dt>Circuit end-to-end (ms)</dt>
              <dd>{formatValue(selected.timing_ms.circuit_end_to_end, 3)}</dd>
            </div>
          </dl>
          <p class="hint">
            Maximum mixing and maximum conversion are distinct. Mixing is unavailable for multiple
            layers or a degenerate generator. Timing scopes differ; these values do not establish
            quantum speedup.
          </p>
          <details>
            <summary>Full reproducibility record</summary>
            <pre>{JSON.stringify(selected, null, 2)}</pre>
          </details>
        {:else}<p>No results yet. Run a simulation to compare both flavor probabilities.</p>{/if}
      </div>
    </Panel>
    <p class="hint">
      The other flavor is an effective active-flavor combination. Smooth profiles, three-flavor
      interference, and neutrino interactions are outside this model. <a href="/methodology/"
        >Read the methodology</a
      >.
    </p>
  </div>
</div>

<style>
  .notice,
  .hint,
  .status {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
  }
  .notice {
    border-left: 3px solid var(--blue);
    padding: 12px 16px;
    background: #f4f7fc;
  }
  .presets {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    margin: 20px 0;
    font-size: 13px;
  }
  .lab-layout {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 24px;
    align-items: start;
  }
  aside,
  .results {
    min-width: 0;
  }
  .results {
    display: grid;
    gap: 20px;
  }
  .status {
    margin: 0;
  }
  form,
  .details {
    padding: 0 24px 24px;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  legend {
    font-size: 14px;
    font-weight: 500;
    margin: 0 0 16px;
  }
  label {
    display: block;
    color: #46546a;
    font-size: 12px;
    margin: 0 0 7px;
  }
  select,
  input {
    width: 100%;
    padding: 10px;
    margin-bottom: 16px;
    background: white;
    border: 1px solid #c3cedb;
    border-radius: 2px;
    color: var(--text);
    font-size: 13px;
    min-height: 40px;
  }
  form .button {
    width: 100%;
  }
  .error {
    padding: 16px;
    border-left: 3px solid #b42318;
    background: #fff0ed;
    color: #8b251c;
    margin: 16px 0;
    font-size: 14px;
    line-height: 1.6;
  }
  .error p {
    margin-bottom: 0;
  }
  .table-scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 12px;
  }
  caption {
    text-align: left;
    margin: 10px 0;
    color: var(--muted);
  }
  th,
  td {
    border-bottom: 1px solid var(--border);
    padding: 12px 8px;
    white-space: nowrap;
  }
  td,
  dd {
    font-family: var(--mono);
  }
  dl {
    margin: 16px 0;
  }
  dl div {
    display: flex;
    gap: 16px;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
  }
  dt {
    color: var(--muted);
  }
  dd {
    margin: 0;
    text-align: right;
  }
  summary {
    cursor: pointer;
    padding: 12px 0;
    font-size: 13px;
  }
  pre {
    max-height: 320px;
    overflow: auto;
    font-size: 11px;
    background: #f4f7fc;
    padding: 12px;
  }
  @media (max-width: 900px) {
    .lab-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
