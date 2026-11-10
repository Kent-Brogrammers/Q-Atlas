import type { CircuitAngle } from '../types';

export const MAX_SOURCE_LENGTH = 20_000;
// Read a bounded amount of UTF-8 text before enforcing the API's character limit.
const MAX_SOURCE_FILE_BYTES = 80_000;

export const DEFAULT_SOURCE = `@qatlas.objective
def assess_selection(choose_red, choose_blue, choose_green):
    selected = choose_red + choose_blue + choose_green
    benefit = choose_red + 2 * choose_blue + 3 * choose_green
    return 10 * (selected - 1)**2 - benefit
`;

export const DEFAULT_SCRIPT = `# Mark one ordinary Python objective. No circuit code is needed.

def describe_selection(value):
    return f"Selection score: {value}"

${DEFAULT_SOURCE}

if __name__ == "__main__":
    score = assess_selection(0, 0, 1)
    print(describe_selection(score))
`;

export function generatedFilename(inputName: string): string {
  const name = inputName.replaceAll('\\', '/').split('/').at(-1) ?? '';
  if (!/\.py$/i.test(name)) return 'q_atlas_generated.py';
  const stem = name
    .slice(0, -3)
    .replace(/[^\p{L}\p{N}._-]/gu, '_')
    .slice(0, 100);
  return `${stem || 'q_atlas'}_qaoa.py`;
}

export async function readObjectiveFile(file: Pick<File, 'size' | 'text'>): Promise<string> {
  if (file.size > MAX_SOURCE_FILE_BYTES) {
    throw new Error('File too large. Load Python source with at most 20,000 characters.');
  }
  const source = await file.text();
  if (!source.trim()) throw new Error('The selected file is empty. Choose a Python source file.');
  if (source.length > MAX_SOURCE_LENGTH) {
    throw new Error('The source exceeds the 20,000-character limit.');
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

export function formatOptionalMs(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return 'Not measured';
  return `${value.toLocaleString('en-US', { maximumFractionDigits: 3 })} ms`;
}
