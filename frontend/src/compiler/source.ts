import type { CircuitAngle } from '../types';

export const MAX_SOURCE_LENGTH = 20_000;
// Read a bounded amount of UTF-8 text before enforcing the API's character limit.
const MAX_SOURCE_FILE_BYTES = 80_000;

export const DEFAULT_FILENAME = 'portfolio_6.py';
export const DEFAULT_SOURCE = `@qatlas.objective  # noqa: F821 - static compiler marker
def plan_projects(solar, insulation, lighting, storage, heating, monitoring):
    selected = solar + insulation + lighting + storage + heating + monitoring
    impact = 8 * solar + 7 * insulation + 6 * lighting + 5 * storage + 4 * heating + 3 * monitoring
    synergy = 2 * solar * storage + insulation * heating
    return 30 * (selected - 3) ** 2 - impact - synergy
`;

export const DEFAULT_SCRIPT = `"""Choose three of six energy projects. Minimize penalty minus impact and synergy."""


${DEFAULT_SOURCE}

if __name__ == "__main__":
    score = plan_projects(1, 1, 1, 0, 0, 0)
    print(f"Portfolio objective: {score}")
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
