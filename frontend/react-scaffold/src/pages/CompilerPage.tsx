import { useState } from 'react';
import { api } from '../api/client';
import { describeError } from '../components/RequestPanel';
import ResponsePanel from '../components/ResponsePanel';

export default function CompilerPage() {
  const [source, setSource] = useState('@qatlas.objective(num_bits=3)\ndef cost(x):\n    return 10*x[0] + 20*x[1] + 15*x[0]*x[1]\n');
  const [result, setResult] = useState<unknown>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function run(benchmark: boolean) {
    setLoading(true); setError(''); setResult(undefined);
    try { setResult(await (benchmark ? api.compilerBenchmark({ source }) : api.analyze({ source }))); }
    catch (caught) { setError(describeError(caught)); }
    finally { setLoading(false); }
  }
  return (
    <>
      <h1 className="text-2xl font-semibold">Python compiler</h1>
      <p className="my-3 text-slate-600">Developer 2 workspace. Submitted Python must only be parsed and validated.</p>
      <p className="mb-5 text-sm text-slate-500">Analysis and benchmarks currently return NOT_IMPLEMENTED.</p>
      <label htmlFor="source" className="font-medium">Objective source</label>
      <textarea id="source" rows={10} maxLength={20000} value={source} onChange={(event) => setSource(event.target.value)} spellCheck={false} />
      <div className="mt-3 flex flex-wrap gap-3">
        <button disabled={loading} onClick={() => void run(false)}>Analyze</button>
        <button disabled={loading} onClick={() => void run(true)}>Run comparison</button>
      </div>
      <ResponsePanel result={result} error={error} loading={loading} />
    </>
  );
}
