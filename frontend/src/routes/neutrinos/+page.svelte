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
      title: 'Vacuum',
      pitch: 'Follow a neutrino through empty space.',
      icon: 'activity',
      tone: 'var(--blue)'
    },
    {
      id: 'density',
      title: 'MSW resonance',
      pitch: 'Find the density where mixing peaks.',
      icon: 'atom',
      tone: 'var(--lab-marker)'
    },
    {
      id: 'layers',
      title: 'Two layers',
      pitch: 'Cross a boundary between two regions.',
      icon: 'layers',
      tone: 'var(--accent)'
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
      <p>Discover how a neutrino changes flavor as it travels through space and matter.</p>
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
        style:--tone={e.tone}
        onclick={() => (settings = preset(e.id))}
        ><span class="emblem"><Icon name={e.icon} size={23} /></span><span
          ><strong>{e.title}</strong><small>{e.pitch}</small></span
        ><span class="radio"></span></button
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
                ? 'Follow the particle through two equal-length regions.'
                : 'Follow the particle from its starting point to the selected distance.'}
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
      <p class="foot">
        The curve updates when you pause. Length, energy and potential use normalized scales.
      </p>
    </aside>
  </div>
  <section class="learn">
    <span class="learn-icon"><Icon name="book" size={22} /></span>
    <div>
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
  </section>
  {#if advanced && run.status === 'ready'}<Inspector
      result={run.result}
      request={run.request}
      {index}
    />{/if}
</div>

<style>
  .lab {
    --lab-selected: color-mix(in srgb, var(--blue) 12%, var(--surface));
    max-width: 1420px;
    margin: auto;
    padding-bottom: 2rem;
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
    letter-spacing: -0.05em;
    font-size: clamp(2.2rem, 4vw, 3.7rem);
    line-height: 1.1;
    margin: 0.15em 0;
  }
  header p,
  .plot-title p,
  .learn p,
  .foot {
    color: var(--muted);
    line-height: 1.6;
  }
  header p {
    max-width: 54ch;
  }
  .switch {
    display: flex;
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 4px;
    flex-shrink: 0;
  }
  .switch button {
    border-radius: 5px;
    padding: 0.5em 0.9em;
    font-size: 0.88rem;
  }
  .switch button[aria-pressed='true'] {
    background: var(--blue);
    color: var(--bg);
    font-weight: 600;
  }
  .choices {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
    margin: 1.65rem 0;
  }
  .choice {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.8rem;
    text-align: left;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 11px;
    padding: 1rem;
    transition: background 0.15s;
  }
  .choice:hover {
    background: var(--surface-raised);
  }
  .choice[aria-pressed='true'] {
    background: color-mix(in srgb, var(--tone) 10%, var(--surface));
    border-color: var(--tone);
  }
  .choice strong {
    display: block;
    font-size: 1rem;
    font-weight: 600;
  }
  .choice small {
    color: var(--muted);
    line-height: 1.4;
    display: block;
    font-size: 0.8rem;
    margin-top: 0.15rem;
  }
  .emblem,
  .learn-icon {
    color: var(--tone);
    display: grid;
    place-items: center;
    flex: none;
  }
  .radio {
    margin-left: auto;
    align-self: flex-start;
    border: 1px solid var(--muted);
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex: none;
  }
  .choice[aria-pressed='true'] .radio {
    background: var(--tone);
    border-color: var(--tone);
  }
  .deck {
    display: grid;
    grid-template-columns: minmax(0, 2.6fr) minmax(225px, 1fr);
    gap: 1rem;
    align-items: start;
  }
  .instrument,
  .controls,
  .learn {
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
    min-width: 0;
    padding: clamp(1rem, 2vw, 1.65rem);
  }
  h2 {
    font-size: 1.2rem;
    font-weight: 500;
    letter-spacing: -0.025em;
  }
  .plot-title {
    align-items: start;
    margin-bottom: 1rem;
  }
  .plot-title p,
  .foot {
    font-size: 0.81rem;
  }
  .source {
    color: var(--muted);
    font: 0.7rem var(--mono);
    white-space: nowrap;
  }
  .readout {
    border-top: 1px solid var(--border);
    margin-top: 1rem;
    padding-top: 1rem;
  }
  .readout-head {
    font-size: 0.8rem;
  }
  output {
    font: 0.78rem var(--mono);
    color: var(--muted);
  }
  .readout input {
    width: 100%;
    accent-color: var(--blue);
    margin: 0.4rem 0;
  }
  .metrics {
    display: flex;
    align-items: end;
    gap: clamp(0.8rem, 3vw, 3rem);
    flex-wrap: wrap;
  }
  .metrics small {
    font-size: 0.8rem;
    color: var(--muted);
  }
  .metrics strong {
    display: block;
    color: var(--blue);
    font: 500 clamp(1.4rem, 3vw, 2.25rem) var(--mono);
    letter-spacing: -0.07em;
  }
  .metrics div:nth-child(2) strong {
    color: var(--accent);
  }
  .metrics em {
    font-size: 0.55em;
    font-style: normal;
    margin-left: 0.12em;
  }
  .metrics p {
    font-size: 0.73rem;
    max-width: 12ch;
    color: var(--muted);
    margin-bottom: 0.45rem;
  }
  .reset {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
  }
  .foot {
    border-top: 1px solid var(--border);
    padding-top: 1rem;
    margin-top: 1.15rem;
  }
  .learn {
    display: flex;
    align-items: start;
    gap: 1rem;
    margin-top: 1rem;
    background: color-mix(in srgb, var(--accent) 6%, var(--surface));
    border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
  }
  .learn-icon {
    color: var(--accent);
    margin-top: 2px;
  }
  .learn p {
    max-width: 95ch;
    margin: 0.45rem 0;
    font-size: 0.93rem;
  }
  .learn details {
    margin-top: 0.7rem;
    font-size: 0.85rem;
  }
  .learn summary {
    cursor: pointer;
    color: var(--accent);
  }
  .controls h3 {
    margin: 1rem 0 0.5rem;
  }
  .controls label {
    font-size: 0.8rem;
  }
  .numbers {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }
  .numbers input,
  select {
    width: 100%;
    background: var(--surface);
    color: inherit;
    border: 1px solid var(--muted);
    padding: 0.4rem;
    border-radius: 5px;
    font-size: 0.82rem;
  }
  .placeholder {
    min-height: 320px;
    display: grid;
    align-content: center;
    justify-items: center;
    gap: 0.8rem;
    text-align: center;
  }
  .placeholder button {
    background: var(--lab-selected);
    padding: 0.6em 1em;
    border-radius: 6px;
  }
  .progress {
    width: 30px;
    height: 4px;
    background: var(--accent);
    border-radius: 3px;
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
    .choices {
      gap: 0.5rem;
    }
    .choice {
      padding: 0.8rem;
    }
    .choice .radio {
      display: none;
    }
    .controls {
      max-width: 100%;
    }
  }
  @media (max-width: 650px) {
    header {
      align-items: start;
      flex-direction: column;
      gap: 0.75rem;
    }
    .choices {
      grid-template-columns: 1fr;
      margin: 1rem 0;
    }
    .choice {
      padding: 0.65rem 0.85rem;
    }
    .choice small {
      margin: 0;
    }
    .choice .radio {
      display: block;
    }
    .plot-title {
      flex-wrap: wrap;
      gap: 0.25rem;
    }
    .learn {
      gap: 0.6rem;
    }
    .metrics p {
      max-width: none;
    }
    .source {
      font-size: 0.65rem;
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
