import { useEffect, useState } from 'react';
import type { CompilerBenchmarkPlan } from '../types';

export default function BenchmarkPlanPanel({ plan }: { plan: CompilerBenchmarkPlan }) {
  const [url, setUrl] = useState('');
  useEffect(() => {
    const next = URL.createObjectURL(new Blob([JSON.stringify(plan, null, 2) + '\n'], { type: 'application/json' }));
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [plan]);

  return (
    <section className="mt-6 rounded-lg border border-amber-200 bg-white p-5" aria-labelledby="benchmark-plan-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="benchmark-plan-heading" className="text-lg font-semibold">Comparison prepared · not executed</h2>
        {url && <a href={url} download="q_atlas_benchmark_plan.json" className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white">Download comparison plan</a>}
      </div>
      <p className="mt-3 text-sm text-slate-700">Both future solvers receive the same verified QUBO. This compares objective optimization; it does not run or time the surrounding Python application.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded bg-slate-50 p-3 text-sm"><h3 className="font-semibold">Classical path</h3><p>Shared classical baseline · no quantum interactions</p><p className="mt-1 text-slate-500">Not run · no runtime or solution measurements</p></div>
        <div className="rounded bg-slate-50 p-3 text-sm"><h3 className="font-semibold">QAOA path</h3><p>Shared QAOA runner · intended target: Aer simulator</p><p className="mt-1 text-slate-500">Simulator and hardware execution disabled</p></div>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-5">
        <div><dt className="text-slate-500">Layers</dt><dd>{plan.config.p}</dd></div>
        <div><dt className="text-slate-500">Shots</dt><dd>{plan.config.shots}</dd></div>
        <div><dt className="text-slate-500">Seed</dt><dd>{plan.config.seed}</dd></div>
        <div><dt className="text-slate-500">Max iterations</dt><dd>{plan.config.max_iterations}</dd></div>
        <div><dt className="text-slate-500">Budget per solver</dt><dd>{plan.config.timeout_seconds}s</dd></div>
      </dl>
      <p className="mt-3 break-words text-xs text-slate-500">Instance: {plan.problem_id}</p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{plan.blockers.map(blocker => <li key={blocker}>{blocker}</li>)}</ul>
      <button type="button" disabled className="mt-4 disabled:cursor-not-allowed">Run comparison — execution disabled</button>
      <details className="mt-4"><summary className="cursor-pointer text-sm font-medium">Reproducibility manifest</summary><pre className="mt-3 max-h-80 overflow-auto text-xs">{JSON.stringify(plan, null, 2)}</pre></details>
    </section>
  );
}
