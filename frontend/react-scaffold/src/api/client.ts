// Preserve the original scaffold's imports while sharing one transport.
import { createApiClient } from '../../../src/api/client.ts';
export { ApiError } from '../../../src/api/client.ts';

// The development proxy keeps port 5174 independent of the API's CORS defaults.
export const api = createApiClient({ baseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api' });
