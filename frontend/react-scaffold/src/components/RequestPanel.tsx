import { useId, useState } from 'react';
import { ApiError } from '../api/client';
import ResponsePanel from './ResponsePanel';

export function describeError(error: unknown): string {
  if (error instanceof ApiError) return `HTTP ${error.status}\n${JSON.stringify(error.body, null, 2)}`;
  if (error instanceof Error) return error.message;
  return 'Request failed.';
}

export default function RequestPanel<T>({ title, description, initialRequest, submit }: {
  title: string; description: string; initialRequest: T; submit: (input: T) => Promise<unknown>;
}) {
  const id = useId();
  const [text, setText] = useState(JSON.stringify(initialRequest, null, 2));
  const [result, setResult] = useState<unknown>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true); setError(''); setResult(undefined);
    try {
      // This editable development form delegates runtime validation to FastAPI.
      setResult(await submit(JSON.parse(text) as T));
    } catch (caught) { setError(describeError(caught)); }
    finally { setLoading(false); }
  }

  return (
    <>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="my-3 text-slate-600">{description}</p>
      <p className="mb-5 text-sm text-slate-500">The API validates requests and returns NOT_IMPLEMENTED until the experiment is ready.</p>
      <form onSubmit={(event) => { event.preventDefault(); void run(); }}>
        <label htmlFor={id} className="font-medium">Request JSON</label>
        <textarea id={id} rows={14} value={text} onChange={(event) => setText(event.target.value)} spellCheck={false} />
        <button className="mt-3" disabled={loading}>Submit request</button>
      </form>
      <ResponsePanel result={result} error={error} loading={loading} />
    </>
  );
}
