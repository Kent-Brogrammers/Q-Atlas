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

export const DEFAULT_SCRIPT = `# A full script: only the marked circuit factory will be replaced.
# This file is compiler input text; the markers are removed in the download.

${DEFAULT_SOURCE}

@qatlas.circuit
def build_circuit():
    # Your old circuit construction goes here. This entire function is replaced.
    from qiskit import QuantumCircuit
    old_circuit = QuantumCircuit(3)
    old_circuit.x(0)
    return old_circuit


if __name__ == "__main__":
    circuit = build_circuit()
    print(circuit)
`;

export function generatedFilename(inputName: string): string {
  const name = inputName.replaceAll('\\', '/').split('/').at(-1) ?? '';
  if (!/\.py$/i.test(name)) return 'q_atlas_generated.py';
  const stem = name.slice(0, -3).replace(/[^\p{L}\p{N}._-]/gu, '_').slice(0, 100);
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
