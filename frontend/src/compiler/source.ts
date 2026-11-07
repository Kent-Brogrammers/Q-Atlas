import type { CircuitAngle } from '../types';

export const MAX_SOURCE_LENGTH = 20_000;
// Read a bounded amount of UTF-8 text before enforcing the API's character limit.
const MAX_SOURCE_FILE_BYTES = 80_000;

export const DEFAULT_SOURCE = `@qatlas.objective(num_bits=3)
def cost(x):
    selected = 0
    benefit = 0
    for i in range(3):
        selected += x[i]
        benefit += (i + 1) * x[i]
    penalty = 10 * (selected - 1)**2
    return penalty - benefit
`;

export async function readObjectiveFile(file: Pick<File, 'size' | 'text'>): Promise<string> {
  if (file.size > MAX_SOURCE_FILE_BYTES) {
    throw new Error('File too large. Load an objective with at most 20,000 characters.');
  }
  const source = await file.text();
  if (!source.trim()) throw new Error('The selected file is empty. Choose a Python objective.');
  if (source.length > MAX_SOURCE_LENGTH) {
    throw new Error('The objective exceeds the 20,000-character limit.');
  }
  // File contents are passed unchanged to the server's allowlisted parser.
  return source;
}

export function formatAngle(angle: CircuitAngle): string {
  if (angle.coefficient === 0) return '0';
  if (angle.coefficient === 1) return angle.parameter;
  if (angle.coefficient === -1) return `-${angle.parameter}`;
  return `${angle.coefficient} × ${angle.parameter}`;
}
