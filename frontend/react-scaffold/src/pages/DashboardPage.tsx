import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { describeError } from '../components/RequestPanel';
import ResponsePanel from '../components/ResponsePanel';

export default function DashboardPage() {
  const [result, setResult] = useState<unknown>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function checkHealth() {
    setLoading(true); setError(''); setResult(undefined);
    try { setResult(await api.health()); }
    catch (caught) { setError(describeError(caught)); }
    finally { setLoading(false); }
  }
  return (
    <>
      <h1 className="text-2xl font-semibold">Experiment workspace</h1>
      <p className="my-3 text-slate-600">A shared starting point for reproducible quantum and classical comparisons.</p>
      <div className="my-6 grid gap-3 sm:grid-cols-2">
        {[
          ['compiler', 'Python compiler', 'Developer 2 · supported Python objectives → canonical QUBO'],
          ['materials', 'Quantum materials', 'Developer 1 · small spin systems and exact references'],
          ['optimization', 'Optimization', 'Developer 3 · shared QAOA and classical baselines'],
          ['search', 'Quantum search', 'Developer 4 · Grover probability and query comparisons'],
        ].map(([path, title, description]) => (
          <Link className="rounded-lg border border-slate-200 bg-white p-5 hover:border-indigo-400" to={`/${path}`} key={path}>
            <h2 className="font-semibold">{title}</h2><p className="mt-2 text-sm text-slate-600">{description}</p>
          </Link>
        ))}
      </div>
      <button disabled={loading} onClick={() => void checkHealth()}>Check API health</button>
      <ResponsePanel result={result} error={error} loading={loading} />
    </>
  );
}
