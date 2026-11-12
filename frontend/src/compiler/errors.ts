import { ApiError } from '../api/client.ts';

export function compilerErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return [
      ...new Set([
        error.message,
        ...(error.body.error.diagnostics ?? []).map((item) => item.message)
      ])
    ]
      .filter(Boolean)
      .join('\n');
  }
  return error instanceof Error ? error.message : fallback;
}
