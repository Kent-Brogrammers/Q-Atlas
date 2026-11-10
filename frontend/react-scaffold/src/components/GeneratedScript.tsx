import { useEffect, useState } from 'react';
import type { GeneratedPythonArtifact } from '../types';
import { generatedFilename } from '../compiler/source';

export default function GeneratedScript({ artifact, inputName }: {
  artifact: GeneratedPythonArtifact;
  inputName: string;
}) {
  const [url, setUrl] = useState('');
  useEffect(() => {
    const next = URL.createObjectURL(new Blob([artifact.source], { type: 'text/x-python;charset=utf-8' }));
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [artifact.source]);

  return (
    <section className="mt-6 rounded-lg border border-indigo-200 bg-white p-5" aria-labelledby="generated-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="generated-heading" className="text-lg font-semibold">Generated Python script</h2>
        {url && <a href={url} download={generatedFilename(inputName)} className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white">Download .py</a>}
      </div>
      <p className="mt-3 text-sm text-slate-700">
        {artifact.replaced_function ? <>Replaced <code>{artifact.replaced_function}()</code>.</> : 'Added a circuit builder.'}
        {' '}Call <code>{artifact.entrypoint}()</code> to construct the parameterized Qiskit circuit.
        Compiler markers were removed and surrounding Python was preserved.
      </p>
      <p className="mt-2 text-sm text-slate-600">Generated, not executed. Qiskit is required when you call the builder locally. The circuit has unbound angles and no measurements, optimizer, or job submission. Review the preserved Python before running the downloaded file.</p>
      <label htmlFor="generated-python" className="mt-4 block text-sm font-medium">Python code</label>
      <textarea id="generated-python" readOnly rows={16} value={artifact.source} spellCheck={false} className="mt-2 text-xs" />
    </section>
  );
}
