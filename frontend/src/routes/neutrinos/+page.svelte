<script lang="ts">
  import Icon from '#lib/components/Icon.svelte';
  import Panel from '#lib/components/Panel.svelte';
  import NeutrinoProbabilityChart from '#lib/components/NeutrinoProbabilityChart.svelte';
  import { formatValue, displaySeries } from '#lib/neutrinos/presentation.ts';
  import type { ProposedNeutrinoResult } from '#lib/neutrinos/proposal.ts';

  // Discussion types only. No agreed capabilities, API request, or fabricated result.
  let result = $state<ProposedNeutrinoResult | null>(null);
  let channels = $derived(displaySeries(result));
  let terminalIndex = $derived((result?.distances_km.length ?? 0) - 1);
</script>

<svelte:head>
  <title>Neutrino Lab · Q-Atlas</title>
  <meta
    name="description"
    content="Neutrino flavor probabilities, classical validation, and Qiskit simulation accuracy. Model support is awaiting backend agreement."
  />
</svelte:head>

<header class="page-heading">
  <div>
    <h1>Neutrino Lab</h1>
    <p>Configure propagation and compare classical and Qiskit flavor probabilities.</p>
  </div>
</header>

<p class="availability">
  <Icon name="info" size={17} /><span
    ><strong>Neutrino backend unavailable.</strong> Controls will be enabled after model capabilities
    and the API are agreed.</span
  >
</p>

<div class="lab-layout">
  <aside aria-label="Experiment configuration">
    <Panel title="Configuration" subtitle="Unavailable · awaiting backend support">
      <div class="configuration">
        <fieldset disabled aria-describedby="configuration-note">
          <legend>Model</legend>
          <label for="neutrino-model">Neutrino model</label>
          <select id="neutrino-model"><option>Awaiting supported models</option></select>
          <label for="initial-flavor">Initial flavor</label>
          <select id="initial-flavor"><option>Awaiting model definition</option></select>
        </fieldset>
        <fieldset disabled>
          <legend>Propagation</legend>
          <label for="neutrino-energy">Energy <span>GeV</span></label>
          <input id="neutrino-energy" type="number" placeholder="Awaiting model limits" />
          <label for="propagation-distance">Distance <span>km</span></label>
          <input id="propagation-distance" type="number" placeholder="Awaiting model limits" />
          <span class="field-label" id="environment-label">Environment</span>
          <div class="environments" role="group" aria-labelledby="environment-label">
            <label><input type="radio" name="environment" value="vacuum" />Vacuum</label>
            <label
              ><input type="radio" name="environment" value="constant_density" />Constant-density
              matter</label
            >
          </div>
        </fieldset>
        <details class="matter-settings">
          <summary>Constant-density parameters</summary>
          <fieldset disabled>
            <legend class="sr-only">Matter parameters · support unconfirmed</legend>
            <label for="matter-density">Mass density, ρ <span>g/cm³</span></label>
            <input id="matter-density" type="number" placeholder="Convention pending agreement" />
            <label for="electron-fraction">Electron fraction, Yₑ</label>
            <input id="electron-fraction" type="number" placeholder="Support unconfirmed" />
          </fieldset>
        </details>
        <fieldset disabled>
          <legend>Execution</legend>
          <label for="neutrino-shots">Requested shots <span>per point</span></label>
          <input id="neutrino-shots" type="number" placeholder="Awaiting sampling method" />
        </fieldset>
        <button type="button" class="button primary" disabled aria-describedby="configuration-note"
          >Run experiment<Icon name="arrow" size={15} /></button
        >
        <p class="field-note" id="configuration-note">
          No model, flavor count, or environment support has been declared. No requests are sent.
        </p>
      </div>
    </Panel>
  </aside>

  <div class="results">
    <Panel title="Flavor probabilities" subtitle="Classical reference and Qiskit simulation">
      <NeutrinoProbabilityChart {result} />
    </Panel>

    <Panel title="Comparison & run details">
      <div class="result-details">
        <details open={result !== null}>
          <summary
            >Classical vs Qiskit<span>{result ? 'Final distance' : 'Unavailable'}</span></summary
          >
          {#if result}
            <div class="comparison-scroll">
              <table>
                <caption>Probabilities at {formatValue(result.distances_km.at(-1))} km</caption>
                <thead
                  ><tr><th>Flavor</th><th>Classical</th><th>Qiskit</th><th>Absolute error</th></tr
                  ></thead
                >
                <tbody>
                  {#each channels as channel}<tr
                      ><th scope="row">{channel.flavor.label}</th><td
                        >{formatValue(channel.values.classical[terminalIndex])}</td
                      ><td>{formatValue(channel.values.qiskit[terminalIndex])}</td><td
                        >{formatValue(channel.values.absolute_error[terminalIndex])}</td
                      ></tr
                    >
                  {:else}<tr><td colspan="4">No supported flavor series available.</td></tr>{/each}
                </tbody>
              </table>
            </div>
            <p>Classical method: {result.metadata.classical_method}. Qiskit Aer simulation.</p>
          {:else}
            <p>
              No comparison available. Supported flavors and both methods’ probabilities must come
              from the backend.
            </p>
          {/if}
        </details>
        <details open={result !== null}>
          <summary
            >Accuracy & error<span>{result ? 'Backend reported' : 'Not evaluated'}</span></summary
          >
          {#if result}
            <dl class="measurements">
              <div>
                <dt>Maximum absolute error</dt>
                <dd>{formatValue(result.metrics.max_absolute_error)}</dd>
              </div>
              <div>
                <dt>Root mean square error</dt>
                <dd>{formatValue(result.metrics.rms_error)}</dd>
              </div>
              <div>
                <dt>Normalization deviation</dt>
                <dd>{formatValue(result.metrics.normalization_deviation)}</dd>
              </div>
              <div>
                <dt>Declared error tolerance</dt>
                <dd>{formatValue(result.metrics.error_tolerance)}</dd>
              </div>
              <div>
                <dt>Within tolerance</dt>
                <dd>
                  {result.metrics.within_tolerance == null
                    ? 'Not evaluated'
                    : result.metrics.within_tolerance
                      ? 'Yes'
                      : 'No'}
                </dd>
              </div>
            </dl>
          {:else}
            <p>
              Absolute and RMS probability errors, normalization deviation, and tolerance assessment
              require a completed comparison. No accuracy values are available.
            </p>
          {/if}
        </details>
        <details open={result !== null}>
          <summary>Circuit & execution<span>{result ? 'Simulated' : 'Not run'}</span></summary>
          {#if result}
            <dl class="measurements">
              <div>
                <dt>Qubits</dt>
                <dd>{formatValue(result.metrics.num_qubits, 0)}</dd>
              </div>
              <div>
                <dt>Circuit depth</dt>
                <dd>{formatValue(result.metrics.circuit_depth, 0)}</dd>
              </div>
              <div>
                <dt>Depth scope</dt>
                <dd>{result.metadata.circuit_depth_scope}</dd>
              </div>
              <div>
                <dt>Shots per point / total</dt>
                <dd>
                  {formatValue(result.metrics.shots_per_point, 0)} / {formatValue(
                    result.metrics.total_shots,
                    0
                  )}
                </dd>
              </div>
              <div>
                <dt>Probability method</dt>
                <dd>{result.metadata.probability_method}</dd>
              </div>
              <div>
                <dt>Classical elapsed time</dt>
                <dd>
                  {result.classical
                    ? `${formatValue(result.classical.elapsed_ms, 3)} ms`
                    : 'Not measured'}
                </dd>
              </div>
              <div>
                <dt>Qiskit elapsed time</dt>
                <dd>
                  {result.quantum
                    ? `${formatValue(result.quantum.elapsed_ms, 3)} ms`
                    : 'Not measured'}
                </dd>
              </div>
              <div>
                <dt>Timing scope</dt>
                <dd>{result.metadata.timing_scope}</dd>
              </div>
            </dl>
          {:else}
            <p>
              No circuit or execution record available. Qubits, depth, actual shots, sampling
              method, and elapsed times will be reported after execution.
            </p>
          {/if}
        </details>
      </div>
    </Panel>

    <details class="panel assumptions">
      <summary>Scientific assumptions</summary>
      <div>
        <p>
          Vacuum and constant-density matter are distinct propagation models. Their availability
          must be declared by the backend; neither is enabled here yet.
        </p>
        <p>
          Flavor channels, mixing parameters, mass differences, and state encoding await the
          scientific model. No two- or three-flavor simulation is assumed.
        </p>
        <p>
          The classical reference must use the same inputs independently of the Qiskit circuit. No
          neutrino physics or error calculation runs in this frontend.
        </p>
        {#if result}<ul>
            {#each result.metadata.assumptions as assumption}<li>{assumption}</li>{/each}
          </ul>{/if}
        <a class="text-link" href="/methodology/"
          >Model scope and validation<Icon name="arrow" size={14} /></a
        >
      </div>
    </details>
  </div>
</div>

<style>
  .availability {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 14px 16px;
    margin: 0 0 24px;
    border-left: 3px solid var(--blue);
    background: var(--surface-raised);
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
  }
  .availability :global(svg) {
    margin-top: 2px;
    color: var(--blue);
  }
  .availability strong {
    color: var(--text);
    font-weight: 500;
  }
  .lab-layout {
    display: grid;
    grid-template-columns: 290px minmax(0, 1fr);
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
  .configuration {
    padding: 0 24px 20px;
  }
  fieldset {
    padding: 0;
    margin: 0 0 20px;
    border: 0;
    min-width: 0;
  }
  legend {
    width: 100%;
    border-top: 1px solid var(--border);
    padding: 16px 0 12px;
    font-size: 13px;
    font-weight: 500;
  }
  fieldset:first-child legend {
    border: 0;
    padding-top: 0;
  }
  label,
  .field-label {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 7px;
    color: var(--muted);
  }
  label > span {
    font-family: var(--mono);
    color: var(--muted);
  }
  select,
  input[type='number'] {
    width: 100%;
    min-height: 40px;
    padding: 9px 10px;
    margin-bottom: 14px;
    background: var(--surface-raised);
    border: 1px solid var(--border);
    border-radius: 2px;
    color: var(--muted);
    font-size: 12px;
    cursor: not-allowed;
    opacity: 1;
  }
  input::placeholder {
    color: var(--muted);
  }
  fieldset > :last-child {
    margin-bottom: 0;
  }
  .environments {
    display: grid;
    gap: 10px;
    padding-top: 5px;
  }
  .environments label {
    justify-content: start;
    align-items: center;
    margin: 0;
  }
  .environments input {
    margin: 0;
  }
  .matter-settings {
    margin: -2px 0 20px;
  }
  .matter-settings summary {
    font-size: 12px;
    color: var(--muted);
    padding: 0 0 12px;
  }
  .matter-settings fieldset {
    margin: 0;
    padding-top: 6px;
  }
  .configuration .button {
    width: 100%;
    font-size: 13px;
  }
  .field-note {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
    margin: 12px 0 0;
  }
  .result-details {
    border-top: 1px solid var(--border);
  }
  .result-details details + details {
    border-top: 1px solid var(--border);
  }
  summary {
    cursor: pointer;
  }
  .result-details summary {
    padding: 17px 24px;
    font-size: 13px;
  }
  .result-details summary span {
    float: right;
    color: var(--muted);
    font-size: 12px;
    margin-left: 12px;
  }
  .result-details p,
  .assumptions p,
  .assumptions li {
    font-size: 13px;
    line-height: 1.7;
    color: var(--muted);
  }
  .result-details p {
    padding: 0 24px 20px;
    margin: 0;
  }
  .comparison-scroll {
    overflow-x: auto;
    margin-bottom: 16px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    text-align: left;
    font-size: 12px;
  }
  caption {
    text-align: left;
    padding: 0 24px 12px;
    color: var(--muted);
  }
  th,
  td {
    padding: 12px 16px;
    border-block: 1px solid var(--border);
    white-space: nowrap;
  }
  th {
    font-weight: 400;
  }
  thead {
    background: var(--surface-raised);
    color: var(--muted);
  }
  td {
    font-family: var(--mono);
  }
  .measurements {
    margin: 0;
    padding: 0 24px 20px;
  }
  .measurements div {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 20px;
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
  }
  dt {
    font-size: 12px;
    color: var(--muted);
  }
  dd {
    font: 12px/1.6 var(--mono);
    margin: 0;
    text-align: right;
    overflow-wrap: anywhere;
  }
  .assumptions summary {
    padding: 20px 24px;
    font-size: 14px;
    font-weight: 500;
  }
  .assumptions > div {
    padding: 0 24px 24px;
  }
  .assumptions p {
    margin: 0 0 12px;
  }
  .assumptions ul {
    list-style: disc;
    padding-left: 18px;
  }
  @media (max-width: 950px) {
    .lab-layout {
      grid-template-columns: 1fr;
    }
    .configuration {
      display: grid;
      grid-template-columns: 1fr 1fr;
      column-gap: 24px;
      align-items: start;
    }
    .configuration > :nth-last-child(-n + 2) {
      grid-column: 1 / -1;
    }
    .matter-settings {
      grid-column: 1;
      grid-row: 2;
    }
  }
  @media (max-width: 600px) {
    .configuration {
      display: block;
      padding-inline: 18px;
    }
    .result-details summary {
      padding-inline: 18px;
    }
    .result-details summary span {
      float: none;
      display: block;
      margin: 6px 0 0 17px;
    }
    .result-details p,
    .measurements {
      padding-inline: 18px;
    }
    .assumptions summary,
    .assumptions > div {
      padding-inline: 18px;
    }
  }
</style>
