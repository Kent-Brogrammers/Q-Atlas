export default function ResponsePanel({ result, error, loading }: {
  result: unknown; error: string; loading: boolean;
}) {
  return (
    <section aria-live="polite" aria-busy={loading} className="mt-5">
      {loading && <p role="status">Waiting for the API…</p>}
      {error && <pre role="alert" className="whitespace-pre-wrap rounded-md bg-amber-50 p-4 text-sm text-amber-900">{error}</pre>}
      {result !== undefined && <pre className="overflow-auto rounded-md bg-white p-4 text-sm">{JSON.stringify(result, null, 2)}</pre>}
    </section>
  );
}
