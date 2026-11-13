<script lang="ts">
  import type { NeutrinoResponse, NeutrinoRequest } from '../../types/index.ts';
  import { formatValue as fmt } from '../neutrinos/presentation.ts';
  let {
    result,
    request,
    index
  }: { result: NeutrinoResponse; request: NeutrinoRequest; index: number } = $props();
  const tabs = ['Results', 'Physics', 'Quantum Circuit', 'Validation', 'Run Record'] as const;
  let tab = $state<(typeof tabs)[number]>('Results');
  let r = $derived(result.results[index]);
  let [a, b] = $derived(r.statevector ?? []);
  let bloch = $derived(
    a && b
      ? [
          2 * (a[0] * b[0] + a[1] * b[1]),
          2 * (a[0] * b[1] - a[1] * b[0]),
          a[0] ** 2 + a[1] ** 2 - b[0] ** 2 - b[1] ** 2
        ]
      : null
  );
  // Orthographic view: horizontal X−Y, vertical Z with a slight tilt towards +X,+Y.
  const project = (v: number[]) => [
    85 + (58 * (v[0] - v[1])) / Math.sqrt(2),
    80 - 58 * (v[2] * Math.cos(0.3) - ((v[0] + v[1]) * Math.sin(0.3)) / Math.sqrt(2))
  ];
  const xyz = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1]
  ];
  function save(name: string, data: unknown) {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>

<section class="inspector">
  <nav aria-label="Scientific inspection">
    {#each tabs as t}<button aria-pressed={tab === t} onclick={() => (tab = t)}>{t}</button>{/each}
  </nav>
  <div class="body">
    {#if tab === 'Results'}
      <h3>Probability at the selected point</h3>
      <p>
        {result.axis === 'distance' ? 'Distance' : 'Potential'}
        {fmt(result.coordinates[index])} · normalized
      </p>
      <div class="scroll">
        <table>
          <thead><tr><th>Method</th><th>Electron flavor</th><th>Other flavor</th></tr></thead><tbody
          >
            {#each [['Analytical', r.analytical], ['SciPy matrix exponential', r.numerical], ['Ideal Qiskit Aer', r.ideal], ['Finite-shot frequency', r.measured]] as [name, p]}
              {#if typeof p === 'object' && p}<tr
                  ><th>{name}</th><td>{p.electron}</td><td>{p.other}</td></tr
                >{/if}{/each}
          </tbody>
        </table>
      </div>
      {#if !r.analytical}<p>
          This point crosses multiple layers. The independent reference applies each layer’s matrix
          exponential in travel order. The single-layer formula applies only within one uniform
          region.
        </p>{/if}
    {:else if tab === 'Physics'}
      <h3>Evolution in the flavor basis</h3>
      <p>
        One qubit has two basis states. Here |0⟩ represents electron flavor and |1⟩ represents one
        effective other flavor. The model starts in |0⟩ and omits the third flavor.
      </p>
      <pre>G = xX + zZ,   k = δ / ε
x = k sin(2θ),   z = s v − k cos(2θ)
U(ℓ) = exp(−i G ℓ)</pre>
      <p>
        δ is signed mass-squared splitting and ε is energy. The matter sign s is +1 for neutrinos
        and −1 for antineutrinos. Increasing energy reduces the vacuum contribution k at fixed
        splitting.
      </p>
      <p>
        In one layer, r = √(x² + z²) and conversion probability is (x²/r²) sin²(rℓ). The first
        factor sets the maximum possible conversion. The phase rℓ determines how much occurs at the
        selected distance. At r = 0 the state stays unchanged.
      </p>
      <p>
        Vacuum mixing angle θ = {fmt(r.configuration.parameters?.theta)} rad. {#if r.analytical?.theta_m != null}Effective
          angle θₘ = {fmt(r.analytical.theta_m)} rad and mixing strength = {fmt(
            r.analytical.mixing_strength
          )}.{:else if r.analytical}The generator is degenerate here, so its effective angle is
          undefined.{:else}Each layer has its own effective angle.{/if}
      </p>
      <p>
        For nonzero transverse mixing, z = 0 gives maximal mixing. {#if result.resonance_potential != null}The
          positive resonant potential is {fmt(result.resonance_potential)}.{:else}These settings
          have no positive-density resonance.{/if} The effective-angle convention is θₘ = ½ atan2(|x|,
        −z).
      </p>
      <h4>Layers traversed at this point</h4>
      <ol>
        {#each r.configuration.layers as l}<li>
            Length {fmt(l.distance)} · potential {fmt(l.potential)}
          </li>{/each}
      </ol>
      <p>
        For two regions the state evolves as U₂ U₁ |0⟩. The state entering the second layer carries
        phase accumulated in the first.
      </p>
      <h4>Normalized units</h4>
      <p>
        Choose reference energy E₀ and mass-squared scale Δ₀. With ℏ = c = 1, δ = Δm²/Δ₀, ε = E/E₀,
        ℓ = L/(4E₀/Δ₀), and v = V/(Δ₀/2E₀). The ordinary matter potential V is proportional to
        electron number density. Axis values express ratios to these scales.
      </p>
    {:else if tab === 'Quantum Circuit'}
      <h3>Executed measurement circuit</h3>
      <p>{r.backend} · {r.num_qubits} qubit · depth {r.circuit_depth} including measurement</p>
      {#if r.circuit_diagram}<pre aria-label="Qiskit circuit diagram">{r.circuit_diagram}</pre>
        <details>
          <summary>Rotation sequence and exact angles</summary>
          <ol>
            {#each r.rotations ?? [] as gate}<li>
                <code>{gate.gate}({gate.angle})</code> on q₀
              </li>{:else}<li>Identity propagation at this point.</li>{/each}
          </ol>
        </details>{:else}<p>
          Restart the updated backend to include the measured circuit in this record.
        </p>{/if}
      <p>
        Qiskit measures q₀ into classical bit 0. A zero counts as electron flavor and a one counts
        as other flavor.
      </p>
      {#if bloch}<div class="state">
          <svg
            viewBox="0 0 170 160"
            width="170"
            role="img"
            aria-label="Bloch vector for the ideal pre-measurement state"
            ><circle cx="85" cy="80" r="58" fill="none" stroke="var(--subtle)" /><ellipse
              cx="85"
              cy="80"
              rx="58"
              ry={58 * Math.sin(0.3)}
              fill="none"
              stroke="var(--lab-border)"
            />{#each xyz as v, i}<line
                x1="85"
                y1="80"
                x2={project(v)[0]}
                y2={project(v)[1]}
                stroke="var(--subtle)"
              /><text x={project(v)[0] + 4} y={project(v)[1] - 3} fill="var(--lab-muted)"
                >{['x', 'y', 'z'][i]}</text
              >{/each}<line
              x1="85"
              y1="80"
              x2={project(bloch)[0]}
              y2={project(bloch)[1]}
              stroke="var(--lab-teal)"
              stroke-width="3"
            /><circle
              cx={project(bloch)[0]}
              cy={project(bloch)[1]}
              r="4"
              fill="var(--lab-teal)"
            /></svg
          >
          <div>
            <h4>Before measurement</h4>
            <p>Bloch coordinates<br /><code>{bloch.map((v) => fmt(v, 5)).join(', ')}</code></p>
          </div>
        </div>{/if}
    {:else if tab === 'Validation'}
      <h3>Numerical agreement</h3>
      <div class="scroll">
        <table>
          <thead><tr><th>Absolute error</th><th>Electron</th><th>Other</th></tr></thead><tbody
            >{#each Object.entries(r.absolute_errors) as [name, p]}{#if p}<tr
                  ><th
                    >{{
                      ideal_vs_numerical: 'Ideal vs SciPy',
                      analytical_vs_numerical: 'Analytical vs SciPy',
                      sampling: 'Shots vs ideal',
                      total: 'Shots vs SciPy'
                    }[name]}</th
                  ><td>{fmt(p.electron)}</td><td>{fmt(p.other)}</td></tr
                >{/if}{/each}</tbody
          >
        </table>
      </div>
      <p>
        The SciPy and ideal state norms are {r.numerics.reference_norm} and {r.numerics.ideal_norm}.
        A normalized state has norm 1. Their state-vector difference is {fmt(
          r.numerics.state_error_l2
        )}. Splitting each constant layer in two changes the reference by {fmt(
          r.numerics.subdivision_check.state_change_l2
        )} in L² norm.
      </p>
      <h4>Measurement statistics</h4>
      <p>
        {r.counts['0'] ?? 0} electron and {r.counts['1'] ?? 0} other outcomes in {r.shots} shots. At the
        ideal other-flavor probability, the expected standard deviation of its sampled fraction is √(p(1−p)/N)
        = {fmt(Math.sqrt(Math.max(0, r.ideal.other * (1 - r.ideal.other)) / r.shots))}. Independent
        samples fluctuate even with an accurate circuit.
      </p>
      <h4>Runtime at this point</h4>
      <dl>
        {#each Object.entries(r.timing_ms) as [name, v]}<div>
            <dt>{name.replaceAll('_', ' ')}</dt>
            <dd>{fmt(v, 3)} ms</dd>
          </div>{/each}
      </dl>
      <p>
        Circuit end-to-end includes construction, transpilation, ideal execution and sampling. SciPy
        timing covers the reference evolution and probability extraction.
      </p>
    {:else}
      <h3>Reproduce this curve</h3>
      <p>
        {result.coordinates.length} evaluated points · {r.shots} shots per point · initial seed {request
          .experiment.seed} · selected seed {r.configuration.seed}
      </p>
      <div class="actions">
        <button onclick={() => save('neutrino-configuration.json', request)}
          >Export configuration</button
        ><button onclick={() => save('neutrino-run.json', { request, result })}
          >Export complete run</button
        >
      </div>
      <details>
        <summary>Submitted configuration</summary>
        <pre>{JSON.stringify(request, null, 2)}</pre>
      </details>
      <details>
        <summary>Full selected-point record</summary>
        <pre>{JSON.stringify(r, null, 2)}</pre>
      </details>
    {/if}
  </div>
</section>

<style>
  .inspector {
    background: var(--lab-panel);
    border: 1px solid var(--lab-border);
    border-radius: 3px;
    overflow: hidden;
    margin-top: 20px;
    min-width: 0;
  }
  nav,
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  nav {
    padding: 0.65rem;
    border-bottom: 1px solid var(--lab-border);
  }
  button {
    padding: 0.5rem 0.8rem;
    border: 1px solid transparent;
    border-radius: 2px;
    background: transparent;
    font-size: 13px;
  }
  button[aria-pressed='true'],
  .actions button {
    background: var(--blue-soft);
    color: var(--blue);
  }
  button:hover {
    border-color: var(--lab-border);
  }
  .body {
    padding: 1.3rem;
  }
  .body p,
  .body li {
    font-size: 13px;
    line-height: 1.65;
    color: var(--lab-muted);
    max-width: 85ch;
    margin: 0.7rem 0;
  }
  h3 {
    font-size: 16px;
    font-weight: 500;
  }
  h4 {
    font-weight: 600;
    margin-top: 1rem;
  }
  .scroll,
  pre {
    overflow: auto;
  }
  pre {
    font: 0.82rem/1.6 var(--mono);
    background: var(--surface-raised);
    padding: 1rem;
    border: 1px solid var(--lab-border);
    border-radius: 2px;
    margin: 1rem 0;
    max-height: 25rem;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.83rem;
  }
  th,
  td {
    text-align: left;
    border-bottom: 1px solid var(--lab-border);
    padding: 0.6rem;
  }
  td,
  dd {
    font-family: var(--mono);
  }
  details {
    margin: 0.9em 0;
  }
  summary {
    cursor: pointer;
  }
  .state {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }
  dl div {
    display: flex;
    justify-content: space-between;
    max-width: 32rem;
    padding: 0.3em;
  }
  ol {
    list-style: decimal;
    padding-left: 1.5em;
  }
</style>
