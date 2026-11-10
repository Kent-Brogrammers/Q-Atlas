import type { CircuitPreview as Preview } from '../types';
import { formatAngle } from '../compiler/source';

export default function CircuitPreview({ circuit }: { circuit: Preview }) {
  return (
    <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5" aria-labelledby="circuit-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="circuit-heading" className="text-lg font-semibold">Symbolic circuit preview</h2>
        <span className="rounded bg-amber-50 px-2 py-1 text-sm text-amber-900">Not executed</span>
      </div>
      <p className="mt-2 text-sm text-slate-600">
        {circuit.num_qubits} qubits · {circuit.p} {circuit.p === 1 ? 'layer' : 'layers'} · Logical depth {circuit.logical_depth}
      </p>
      <p className="mt-2 text-sm text-slate-600">
        This gate plan has no samples or optimized angles. Transpiled depth is unavailable.
        The intended execution target is the Aer simulator.
      </p>
      <p className="mt-3 text-sm">Parameter order: <code>{circuit.parameters.join(', ')}</code></p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Ordered symbolic gates, with x[i] mapped to qubit i</caption>
          <thead className="border-b border-slate-200">
            <tr><th className="p-2">Step</th><th className="p-2">Gate</th><th className="p-2">Qubits</th><th className="p-2">Angle (radians)</th></tr>
          </thead>
          <tbody>
            {circuit.gates.map((gate, index) => (
              <tr key={index} className="border-b border-slate-100">
                <td className="p-2">{index + 1}</td>
                <td className="p-2 font-mono">{gate.name.toUpperCase()}</td>
                <td className="p-2 font-mono">{gate.qubits.map((i) => `x[${i}] / q${i}`).join(', ')}</td>
                <td className="p-2 font-mono">{gate.angle ? formatAngle(gate.angle) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-sm">Global phase: <code>{circuit.global_phase.map(formatAngle).join(' + ')}</code></p>
    </section>
  );
}
