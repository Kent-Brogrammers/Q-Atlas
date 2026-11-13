<script lang="ts">
  import { onDestroy } from 'svelte';
  import { api } from '../../api/client.ts';
  import Chart from '#lib/components/NeutrinoProbabilityChart.svelte';
  import Inspector from '#lib/components/NeutrinoInspector.svelte';
  import Parameter from '#lib/components/LabParameter.svelte';
  import Icon from '#lib/components/Icon.svelte';
  import { preset, createLabRunner, type RunState } from '#lib/neutrinos/session.ts';
  import { formatValue as fmt } from '#lib/neutrinos/presentation.ts';
  const experiments = [
    {
      id: 'vacuum',
      title: 'Vacuum'
    },
    {
      id: 'density',
      title: 'MSW resonance'
    },
    {
      id: 'layers',
      title: 'Two layers'
    }
  ] as const;
  const percent = (p: number) => (p > 0 && p < 0.0001 ? '<0.01' : fmt(p * 100, 2));
  let settings = $state(preset('vacuum')),
    advanced = $state(false),
    index = $state(0);
  let run = $state<RunState>({ status: 'waiting' });
  const runner = createLabRunner(
    (req, signal) => api.neutrinos(req, signal),
    (state) => {
      if (state.status === 'ready')
        index =
          state.result.axis === 'potential'
            ? Math.floor(state.result.results.length / 2)
            : state.result.results.length - 1;
      run = state;
    }
  );
  $effect(() => {
    runner.update({ ...settings });
  });
  onDestroy(() => runner.dispose());
  let experiment = $derived(
    experiments.find(
      (e) => e.id === (settings.environment === 'matter' ? 'density' : settings.environment)
    )!
  );
  let point = $derived(run.status === 'ready' ? run.result.results[index] : null);
  let coordinate = $derived(run.status === 'ready' ? run.result.coordinates[index] : null);
  let density = $derived(settings.environment === 'density');
</script>

<svelte:head
  ><title>Neutrino Lab · Q-Atlas</title><meta
    name="description"
    content="Explore how distance and matter change neutrino flavor in a two-flavor quantum simulation."
  /></svelte:head
>
<div class="lab">
  <header>
    <div>
      <h1>Neutrino Lab</h1>
      <p>Compare two-flavor propagation in vacuum and matter.</p>
    </div>
    <div class="switch" aria-label="Laboratory mode">
      <button aria-pressed={!advanced} onclick={() => (advanced = false)}>Explore</button><button
        aria-pressed={advanced}
        onclick={() => (advanced = true)}>Advanced</button
      >
    </div>
  </header>
  <div class="choices" aria-label="Experiment">
    {#each experiments as e}
      <button
        class="choice"
        aria-pressed={experiment.id === e.id}
        onclick={() => (settings = preset(e.id))}>{e.title}</button
      >
    {/each}
  </div>
  <div class="deck">
    <section class="instrument">
      <div class="plot-title">
        <div>
          <h2>Flavor probability</h2>
          <p>
            {density
              ? 'Vary matter potential at a fixed travel distance of ' +
                fmt(settings.distance) +
                '.'
              : settings.environment === 'layers'
                ? 'Propagation through two equal-length regions.'
                : 'Probability along the propagation path.'}
          </p>
        </div>
        <span class="source">Aer simulator</span>
      </div>
      {#if run.status === 'ready' && point}
        <Chart result={run.result} bind:index {advanced} />
        <div class="readout">
          <div class="readout-head">
            <label for="inspect">Inspect a point</label><output
              >{density ? 'Potential' : 'Distance'} {fmt(coordinate, 4)}</output
            >
          </div>
          <input
            id="inspect"
            aria-label="Selected graph point"
            type="range"
            min="0"
            max={run.result.results.length - 1}
            step="1"
            bind:value={index}
          />
          <div class="metrics">
            <div>
              <small>Electron flavor</small><strong
                >{percent(point.ideal.electron)}<em>%</em></strong
              >
            </div>
            <div>
              <small>Other flavor</small><strong>{percent(point.ideal.other)}<em>%</em></strong>
            </div>
            <p>Ideal detection chances at this point</p>
          </div>
        </div>
      {:else}<div class="placeholder" aria-live="polite">
          {#if run.status === 'error'}<strong>Unable to plot this run</strong>
            <p>{run.message}</p>
            <button onclick={() => runner.update({ ...settings }, 0)}>Retry simulation</button
            >{:else}<span class="progress"></span><strong
              >{run.status === 'running'
                ? 'Simulating flavor probabilities…'
                : 'Preparing your curve…'}</strong
            >{/if}
        </div>{/if}
    </section>
    <aside class="controls">
      <div class="control-title">
        <h2>Controls</h2>
        <button class="reset" onclick={() => (settings = preset(settings.environment))}
          ><Icon name="reset" size={14} /> Reset</button
        >
      </div>
      {#if advanced && experiment.id === 'density'}<label for="scan">Matter experiment</label
        ><select id="scan" bind:value={settings.environment}
          ><option value="density">Sweep matter potential</option><option value="matter"
            >Travel at constant density</option
          ></select
        >{/if}
      <Parameter
        label="Travel distance"
        unit="L/L₀"
        help={density
          ? 'Baseline held fixed across the density sweep.'
          : 'Length of the path through this environment.'}
        min={0}
        max={100}
        bind:value={settings.distance}
      />
      {#if settings.environment === 'layers' || settings.environment === 'matter'}<Parameter
          label={settings.environment === 'layers' ? 'First layer potential' : 'Matter potential'}
          unit="V/V₀"
          help="Higher potential represents more electrons per unit volume."
          min={0}
          max={10}
          bind:value={settings.potential}
        />{/if}
      {#if settings.environment === 'layers'}<Parameter
          label="Second layer potential"
          unit="V/V₀"
          help="Potential after the halfway point."
          min={0}
          max={10}
          bind:value={settings.second_potential}
        />{/if}
      {#if density}<Parameter
          label="Sweep limit"
          unit="V/V₀"
          help="The largest matter potential on the horizontal axis."
          min={0}
          max={10}
          bind:value={settings.max_potential}
        />{/if}
      {#if advanced || experiment.id === 'vacuum'}<Parameter
          label="Mixing angle"
          unit="rad"
          help="Sets how the two mass states combine into a flavor."
          min={0}
          max={Math.PI / 2}
          bind:value={settings.theta}
        />{/if}
      {#if advanced}
        <Parameter
          label="Energy"
          unit="E/E₀"
          help="At fixed mass splitting, energy changes the oscillation phase."
          min={0.01}
          max={100}
          bind:value={settings.energy}
        />
        <Parameter
          label="Mass-squared splitting"
          unit="Δm²/Δ₀"
          help="Signed difference between the squared masses."
          min={-10}
          max={10}
          bind:value={settings.delta_m2}
        />
        <label for="particle">Particle</label><select id="particle" bind:value={settings.particle}
          ><option value="neutrino">Neutrino</option><option value="antineutrino"
            >Antineutrino</option
          ></select
        >
        <h3>Sampling</h3>
        <div class="numbers">
          <label>Points<input type="number" min="2" max="41" bind:value={settings.samples} /></label
          ><label
            >Shots / point<input
              type="number"
              min="1"
              max="100000"
              bind:value={settings.shots}
            /></label
          ><label
            >Initial seed<input
              type="number"
              min="0"
              max="4294967295"
              bind:value={settings.seed}
            /></label
          >
        </div>
      {/if}
      <p class="foot">Updates automatically. All quantities use normalized scales.</p>
    </aside>
  </div>
  <details class="learn">
    <summary>Physical model and assumptions</summary>
    <div class="learn-content">
      <h2>
        {settings.environment === 'vacuum'
          ? 'Why does flavor change in empty space?'
          : settings.environment === 'layers'
            ? 'What happens at the boundary?'
            : 'How does matter change mixing?'}
      </h2>
      {#if settings.environment === 'vacuum'}<p>
          An electron-flavor neutrino starts as a combination of two mass states. They accumulate
          phase at different rates as they travel. Their interference changes the chance of
          detecting each flavor. The mixing angle controls how large that swing can be.
        </p>
      {:else if settings.environment === 'layers'}<p>
          The neutrino carries its state across the boundary. The second potential changes how the
          state evolves from there. Follow the marker across the shaded region to see how the
          detection chances develop.
        </p>
      {:else}<p>
          Electrons in matter change how the two flavors mix. At resonance they mix maximally. The
          distance traveled still determines the oscillation phase, so even maximal mixing can give
          a small conversion probability.
        </p>{/if}
      {#if point?.analytical?.mixing_strength != null}<p>
          At this point the mixing allows up to <b
            >{fmt(point.analytical.mixing_strength * 100, 2)}%</b
          >
          conversion. The ideal conversion probability at the sampled distance is
          <b>{percent(point.ideal.other)}%</b>.
        </p>{/if}
      <details>
        <summary>What are flavor, qubits and shots?</summary>
        <p>
          Flavor describes how a neutrino interacts when detected. One simulated qubit can represent
          the two outcomes in this simplified model. A shot prepares and measures the circuit once.
          Repeating it estimates the probability of each outcome.
        </p>
      </details>
    </div>
  </details>
  {#if advanced && run.status === 'ready'}<Inspector
      result={run.result}
      request={run.request}
      {index}
    />{/if}
</div>

<style>
  .lab {
    --lab-panel: var(--surface);
    --lab-border: var(--border);
    --lab-muted: var(--muted);
    --lab-teal: var(--cyan);
    max-width: 1280px;
    margin: auto;
    padding-bottom: 1rem;
  }
  header,
  .control-title,
  .plot-title,
  .readout-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }
  h1 {
    font-weight: 500;
    letter-spacing: -0.04em;
    font-size: 30px;
    line-height: 1.2;
    margin: 0 0 8px;
  }
  header p,
  .plot-title p,
  .learn p,
  .foot {
    color: var(--lab-muted);
    line-height: 1.7;
  }
  header p {
    margin: 0;
    font-size: 14px;
  }
  .switch {
    display: flex;
    border: 1px solid var(--lab-border);
    border-radius: 3px;
    padding: 3px;
    background: var(--surface);
    flex-shrink: 0;
  }
  .switch button {
    border: 0;
    background: transparent;
    color: var(--muted);
    border-radius: 2px;
    padding: 8px 12px;
    font-size: 13px;
  }
  .switch button[aria-pressed='true'] {
    background: var(--blue-soft);
    color: var(--blue);
    font-weight: 500;
  }
  .choices {
    display: flex;
    border-bottom: 1px solid var(--lab-border);
    margin: 26px 0 24px;
  }
  .choice {
    min-height: 44px;
    text-align: center;
    padding: 12px 24px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--muted);
    font-size: 14px;
    transition:
      background 0.15s,
      color 0.15s;
  }
  .choice:hover {
    color: var(--blue);
    background: var(--blue-soft);
  }
  .choice[aria-pressed='true'] {
    border-bottom-color: var(--blue);
    color: var(--blue);
    font-weight: 500;
  }
  .deck {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 280px;
    gap: 20px;
    align-items: start;
  }
  .instrument,
  .controls {
    border: 1px solid var(--lab-border);
    border-radius: 3px;
    background: var(--lab-panel);
    min-width: 0;
    padding: 24px;
  }
  h2 {
    font-size: 17px;
    font-weight: 500;
    letter-spacing: -0.015em;
    margin: 0;
  }
  .plot-title {
    align-items: start;
    margin-bottom: 24px;
  }
  .plot-title p {
    margin: 7px 0 0;
    font-size: 13px;
  }
  .source {
    color: var(--muted);
    font: 11px/1.7 var(--mono);
    white-space: nowrap;
  }
  .readout {
    border-top: 1px solid var(--lab-border);
    margin-top: 20px;
    padding-top: 18px;
  }
  .readout-head {
    font-size: 12px;
  }
  output {
    font: 11px var(--mono);
    color: var(--lab-muted);
  }
  .readout input {
    width: 100%;
    accent-color: var(--blue);
    margin: 12px 0 18px;
  }
  .metrics {
    display: flex;
    align-items: end;
    gap: clamp(20px, 3vw, 48px);
    flex-wrap: wrap;
  }
  .metrics small {
    font-size: 12px;
    color: var(--lab-muted);
  }
  .metrics strong {
    display: block;
    color: var(--blue);
    font: 400 clamp(24px, 2.5vw, 30px)/1.5 var(--mono);
    letter-spacing: -0.06em;
  }
  .metrics div:nth-child(2) strong {
    color: var(--lab-teal);
  }
  .metrics em {
    font-size: 0.55em;
    font-style: normal;
    margin-left: 0.12em;
  }
  .metrics p {
    font-size: 11px;
    max-width: 18ch;
    line-height: 1.6;
    color: var(--lab-muted);
    margin: 0 0 7px;
  }
  .reset {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 0 5px 5px;
    border: 0;
    background: transparent;
    color: var(--blue);
    font-size: 12px;
  }
  .foot {
    border-top: 1px solid var(--lab-border);
    padding-top: 16px;
    margin: 20px 0 0;
    font-size: 11px;
  }
  .learn {
    margin-top: 20px;
    border: 1px solid var(--lab-border);
    border-radius: 3px;
    background: var(--surface);
  }
  .learn > summary {
    padding: 18px 24px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
  }
  .learn-content {
    padding: 0 24px 20px;
    max-width: 95ch;
  }
  .learn h2 {
    font-size: 15px;
  }
  .learn p {
    margin: 10px 0;
    font-size: 13px;
  }
  .learn details {
    margin-top: 16px;
    font-size: 13px;
  }
  .learn details summary {
    cursor: pointer;
    color: var(--blue);
  }
  .controls h3 {
    font-size: 14px;
    font-weight: 500;
    margin: 24px 0 12px;
    padding-top: 20px;
    border-top: 1px solid var(--lab-border);
  }
  .controls label {
    font-size: 12px;
  }
  .numbers {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .numbers input,
  select {
    width: 100%;
    min-width: 0;
    background: var(--surface);
    color: var(--text);
    border: 1px solid #bac7d7;
    padding: 8px;
    border-radius: 2px;
    font-size: 12px;
    margin-top: 6px;
  }
  .placeholder {
    min-height: 370px;
    display: grid;
    align-content: center;
    justify-items: center;
    gap: 12px;
    text-align: center;
    color: var(--muted);
    font-size: 14px;
  }
  .placeholder p {
    max-width: 50ch;
    line-height: 1.7;
  }
  .placeholder button {
    background: var(--blue);
    color: #fff;
    border: 1px solid var(--blue);
    padding: 10px 16px;
    border-radius: 2px;
  }
  .progress {
    width: 30px;
    height: 3px;
    background: var(--blue);
    animation: pulse 1s ease-in-out infinite alternate;
  }
  @keyframes pulse {
    to {
      opacity: 0.3;
    }
  }
  @media (max-width: 900px) {
    .deck {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 650px) {
    header {
      align-items: start;
      flex-direction: column;
      gap: 18px;
    }
    h1 {
      font-size: 27px;
    }
    .choices {
      margin: 20px 0;
    }
    .choice {
      flex: 1;
      min-width: 0;
      padding: 12px 8px;
      font-size: 13px;
    }
    .instrument,
    .controls {
      padding: 20px;
    }
    .plot-title {
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 20px;
    }
    .metrics {
      gap: 24px;
    }
    .metrics p {
      max-width: none;
      width: 100%;
      margin-top: -16px;
    }
    .learn > summary {
      padding: 18px 20px;
    }
    .learn-content {
      padding-inline: 20px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .choice {
      transition: none;
    }
    .progress {
      animation: none;
    }
  }
</style>
