import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { ApiError, api } from '../api/client';
import type { CompilerAnalyzeResult, CompilerBenchmarkResult, GeneratedPythonArtifact } from '../types';
import { DEFAULT_SCRIPT, DEFAULT_SOURCE, MAX_SOURCE_LENGTH, readObjectiveFile } from '../compiler/source';
import CompilerAnalysisPanel from '../components/CompilerAnalysisPanel';
import GeneratedScript from '../components/GeneratedScript';
import ResponsePanel from '../components/ResponsePanel';

export default function CompilerPage() {
  const [source, setSource] = useState(DEFAULT_SCRIPT);
  const [fileName, setFileName] = useState('example.py');
  const [mode, setMode] = useState<'generate' | 'analyze'>('generate');
  const [layers, setLayers] = useState(1);
  const [analysis, setAnalysis] = useState<CompilerAnalyzeResult>();
  const [artifact, setArtifact] = useState<GeneratedPythonArtifact>();
  const [comparison, setComparison] = useState<CompilerBenchmarkResult>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState<'generate' | 'analyze' | 'benchmark' | null>(null);
  const [reading, setReading] = useState(false);
  const editor = useRef<HTMLTextAreaElement>(null);
  const revision = useRef(0);
  const fileRead = useRef(0);
  const pending = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; revision.current++; fileRead.current++; };
  }, []);

  function invalidate() {
    revision.current++;
    setAnalysis(undefined);
    setArtifact(undefined);
    setComparison(undefined);
    setError('');
  }

  function changeSource(text: string, name = 'Pasted source') {
    invalidate();
    setSource(text);
    setFileName(name);
  }

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    invalidate();
    const currentRevision = revision.current;
    const currentRead = ++fileRead.current;
    setReading(true);
    try {
      const text = await readObjectiveFile(file);
      if (mounted.current && revision.current === currentRevision && fileRead.current === currentRead) {
        changeSource(text, file.name);
      }
    } catch (caught) {
      if (mounted.current && revision.current === currentRevision && fileRead.current === currentRead) {
        setError(caught instanceof Error ? caught.message : 'The selected file could not be read.');
      }
    } finally {
      if (mounted.current && fileRead.current === currentRead) setReading(false);
    }
  }

  async function run(kind: 'generate' | 'analyze' | 'benchmark') {
    if (pending.current || reading || !source.trim()) return;
    if (kind === 'benchmark' && analysis?.status !== 'supported') return;
    pending.current = true;
    const currentRevision = revision.current;
    setLoading(kind);
    setError('');
    setComparison(undefined);
    if (kind !== 'benchmark') { setAnalysis(undefined); setArtifact(undefined); }
    try {
      if (kind === 'generate') {
        const result = await api.generateScript({ source, p: layers });
        if (mounted.current && revision.current === currentRevision) {
          setAnalysis(result);
          setArtifact(result.artifact ?? undefined);
        }
      } else if (kind === 'analyze') {
        const result = await api.analyze({ source });
        if (mounted.current && revision.current === currentRevision) setAnalysis(result);
      } else {
        const result = await api.compilerBenchmark({ source });
        if (mounted.current && revision.current === currentRevision) setComparison(result);
      }
    } catch (caught) {
      if (mounted.current && revision.current === currentRevision) {
        if (caught instanceof ApiError && caught.status === 501) {
          setError('Comparison is waiting for the shared solvers from Developer 3. Your analysis and symbolic preview are still available.');
        } else if (caught instanceof ApiError) {
          const diagnostics = caught.body.error.diagnostics ?? [];
          setError([caught.body.error.message, ...diagnostics.map((item) =>
            `${item.line ? `Line ${item.line}: ` : ''}${item.message}`)].join('\n'));
        } else {
          setError(caught instanceof Error ? caught.message : 'The request failed. Check the API connection.');
        }
      }
    } finally {
      pending.current = false;
      if (mounted.current) setLoading(null);
    }
  }

  function selectLine(line: number) {
    const element = editor.current;
    if (!element) return;
    const start = line <= 1 ? 0 : source.split('\n').slice(0, line - 1).join('\n').length + 1;
    const end = source.indexOf('\n', start);
    element.focus();
    element.setSelectionRange(start, end < 0 ? source.length : end);
  }

  const busy = loading !== null || reading;
  return (
    <>
      <h1 className="text-2xl font-semibold">Python-to-circuit compiler</h1>
      <p className="my-3 text-slate-600">Load a .py file, translate a marked binary objective, and download Python with a new QAOA circuit builder.</p>
      <p className="mb-5 text-sm text-slate-500">Supports 1–6 bits, numeric local variables, bounded literal range loops, and squared penalties. Source is parsed and verified; it is never executed.</p>
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Compiler workflow">
        <button type="button" aria-pressed={mode === 'generate'} className={mode === 'generate' ? '' : 'bg-white text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-50'} disabled={busy} onClick={() => { invalidate(); setMode('generate'); }}>Generate script</button>
        <button type="button" aria-pressed={mode === 'analyze'} className={mode === 'analyze' ? '' : 'bg-white text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-50'} disabled={busy} onClick={() => { invalidate(); setMode('analyze'); }}>Analyze objective only</button>
      </div>
      {mode === 'generate' ? (
        <p className="mb-4 text-sm text-slate-600">Keep one <code>@qatlas.objective(num_bits=N)</code> function. Mark an existing zero-argument circuit factory with <code>@qatlas.circuit</code> to replace it. Other Python stays in place. Without a circuit marker, a new builder is appended.</p>
      ) : <p className="mb-4 text-sm text-slate-600">Analyze accepts a single marked objective without surrounding script code. Live comparison awaits the shared solvers.</p>}
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div>
          <label htmlFor="objective-file" className="block text-sm font-medium">Load a Python file</label>
          <input id="objective-file" type="file" accept=".py,text/plain,text/x-python" disabled={reading} onChange={(event) => void loadFile(event)} className="mt-1 block max-w-full text-sm" />
        </div>
        <button type="button" disabled={busy} onClick={() => changeSource(mode === 'generate' ? DEFAULT_SCRIPT : DEFAULT_SOURCE, 'example.py')}>Load example</button>
        {mode === 'generate' && <div>
          <label htmlFor="circuit-layers" className="block text-sm font-medium">QAOA layers</label>
          <select id="circuit-layers" value={layers} disabled={busy} onChange={(event) => { invalidate(); setLayers(Number(event.target.value)); }} className="mt-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm">
            {Array.from({ length: 8 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
          </select>
        </div>}
      </div>
      <label htmlFor="source" className="font-medium">Python source</label>
      <textarea ref={editor} id="source" rows={13} maxLength={MAX_SOURCE_LENGTH} value={source} onChange={(event) => changeSource(event.target.value)} spellCheck={false} />
      <p className="mt-2 break-words text-xs text-slate-500">{fileName} · {source.length.toLocaleString()} / 20,000 characters</p>
      <div className="mt-3 flex flex-wrap gap-3">
        <button type="button" disabled={busy || !source.trim()} onClick={() => void run(mode)}>{mode === 'generate' ? 'Generate Python script' : 'Analyze'}</button>
        {mode === 'analyze' && <button type="button" disabled={busy || analysis?.status !== 'supported'} onClick={() => void run('benchmark')}>Run comparison</button>}
      </div>
      <div aria-live="polite" aria-busy={busy}>
        {reading && <p role="status" className="mt-4">Reading the selected file as text…</p>}
        {loading && <p role="status" className="mt-4">{loading === 'generate' ? 'Generating Python script…' : loading === 'analyze' ? 'Analyzing objective…' : 'Requesting comparison…'} Changes to the source invalidate these results.</p>}
        {error && <p role="alert" className="mt-4 whitespace-pre-wrap rounded-md bg-amber-50 p-4 text-sm text-amber-900">{error}</p>}
        {artifact && <GeneratedScript artifact={artifact} inputName={fileName} />}
        {analysis && <CompilerAnalysisPanel analysis={analysis} selectLine={selectLine} />}
      </div>
      {comparison && <ResponsePanel result={comparison} error="" loading={false} />}
    </>
  );
}
