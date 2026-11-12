import { ApiError } from '../api/client.ts';

export const HARDWARE_REQUEST_STORAGE_KEY = 'qatlas-compiler-qpu-request';

export function isMissingHardwareRequest(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.status === 422 || error.status === 404) &&
    (error.body.error.diagnostics ?? []).some((item) => item.code === 'HARDWARE_REQUEST_NOT_FOUND')
  );
}

/** User-invoked browser cleanup only; keep backend records and quota reservations. */
export function clearMissingHardwareReference(
  storage: Pick<Storage, 'getItem' | 'removeItem'>,
  requestId: string,
  error: unknown
): void {
  if (!requestId || !isMissingHardwareRequest(error)) {
    throw new Error('Check the saved hardware request before clearing its browser reference.');
  }
  if (storage.getItem(HARDWARE_REQUEST_STORAGE_KEY) !== requestId) {
    throw new Error('The saved hardware request changed. Reload and recover the current request.');
  }
  storage.removeItem(HARDWARE_REQUEST_STORAGE_KEY);
}
