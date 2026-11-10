import type { CompilerAnalyzeResult } from '../types';
import CircuitPreview from './CircuitPreview';

export default function CompilerAnalysisPanel({ analysis, selectLine }: {
  analysis: CompilerAnalyzeResult;
  selectLine: (line: number) => void;
}) {
  const qubo = analysis.qubo;
  const pairs = qubo?.quadratic ?? [];
  return (
    <>
      <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5" aria-labelledby="analysis-heading">
        <h2 id="analysis-heading" className="text-lg font-semibold">
          {analysis.status === 'supported' ? 'Objective analyzed' : 'Source rejected'}
        </h2>
        <ul className="mt-3 space-y-3">
          {analysis.diagnostics.map((diagnostic, index) => (
            <li key={index} className="text-sm">
              <span className="mr-2 font-semibold">{diagnostic.severity.toUpperCase()}</span>
              <code className="text-slate-600">{diagnostic.code}</code>
              <p className="mt-1">{diagnostic.message}</p>
              {diagnostic.line != null && (
                <button type="button" className="mt-1 px-2 py-1 text-xs" onClick={() => selectLine(diagnostic.line!)}>
                  Line {diagnostic.line}{diagnostic.column != null ? `, column ${diagnostic.column}` : ''}
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
      {analysis.status === 'supported' && qubo && (
        <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5" aria-labelledby="qubo-heading">
          <h2 id="qubo-heading" className="text-lg font-semibold">Extracted QUBO</h2>
          <p className="mt-2 text-sm text-slate-600">Coefficients calculated from your source, with {qubo.num_variables} binary variables.</p>
          <dl className="mt-4 grid gap-3 sm:grid-cols-3">
            <div><dt className="text-sm text-slate-500">Constant offset</dt><dd className="font-mono">{qubo.constant ?? 0}</dd></div>
            <div><dt className="text-sm text-slate-500">Original sense</dt><dd>{qubo.original_sense ?? 'minimize'}</dd></div>
            <div><dt className="text-sm text-slate-500">Solver sense</dt><dd>minimize</dd></div>
          </dl>
          {qubo.original_sense === 'maximize' && (
            <p className="mt-3 text-sm text-indigo-800">The entire objective was negated for minimization. Negate solver values to recover original maximization values.</p>
          )}
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <table className="w-full text-left text-sm">
              <caption className="mb-2 text-left font-medium">Linear terms</caption>
              <thead><tr><th className="p-2">Variable</th><th className="p-2">Coefficient</th></tr></thead>
              <tbody>{qubo.linear.map((coefficient, i) => (
                <tr key={i} className="border-t border-slate-100"><td className="p-2 font-mono">x[{i}]</td><td className="p-2 font-mono">{coefficient}</td></tr>
              ))}</tbody>
            </table>
            {pairs.length > 0 ? (
              <table className="w-full text-left text-sm">
                <caption className="mb-2 text-left font-medium">Pair terms</caption>
                <thead><tr><th className="p-2">Variables</th><th className="p-2">Coefficient</th></tr></thead>
                <tbody>{pairs.map((term) => (
                  <tr key={`${term.i}-${term.j}`} className="border-t border-slate-100"><td className="p-2 font-mono">x[{term.i}] × x[{term.j}]</td><td className="p-2 font-mono">{term.coefficient}</td></tr>
                ))}</tbody>
              </table>
            ) : <p className="text-sm text-slate-600">No pair terms.</p>}
          </div>
          <p className="mt-3 text-sm text-slate-500">Unused variables keep their declared positions. Assignment strings put x[0] first.</p>
        </section>
      )}
      {analysis.status === 'supported' && analysis.circuit && <CircuitPreview circuit={analysis.circuit} />}
      <details className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-medium">Raw analysis JSON</summary>
        <pre className="mt-3 overflow-auto text-xs">{JSON.stringify(analysis, null, 2)}</pre>
      </details>
    </>
  );
}
