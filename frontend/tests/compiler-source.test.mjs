import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DEFAULT_SCRIPT, MAX_SOURCE_LENGTH, generatedFilename, readObjectiveFile } from '../src/compiler/source.ts';

test('reads source as unchanged text, including unsupported input for server validation', async () => {
  const text = "import os\nprint('source text only')\n";
  assert.equal(await readObjectiveFile({ size: text.length, text: async () => text }), text);
});

test('rejects oversized files before reading their contents', async () => {
  let read = false;
  await assert.rejects(readObjectiveFile({ size: 80_001, text: async () => { read = true; return 'x'; } }), /too large/);
  assert.equal(read, false);
});

test('enforces the character limit independently of the byte guard', async () => {
  const text = 'x'.repeat(MAX_SOURCE_LENGTH + 1);
  await assert.rejects(readObjectiveFile({ size: text.length, text: async () => text }), /character limit/);
  const boundary = 'x'.repeat(MAX_SOURCE_LENGTH);
  assert.equal(await readObjectiveFile({ size: boundary.length, text: async () => boundary }), boundary);
});

test('rejects empty files and preserves read failures', async () => {
  await assert.rejects(readObjectiveFile({ size: 3, text: async () => ' \n ' }), /empty/);
  await assert.rejects(readObjectiveFile({ size: 1, text: async () => { throw new Error('Read failed'); } }), /Read failed/);
});

test('generated downloads use a safe Python filename', () => {
  assert.equal(generatedFilename('model.py'), 'model_qaoa.py');
  assert.equal(generatedFilename('C:\\inputs\\Cost.PY'), 'Cost_qaoa.py');
  assert.equal(generatedFilename('../cost file.py'), 'cost_file_qaoa.py');
  assert.equal(generatedFilename('Pasted source'), 'q_atlas_generated.py');
  assert.equal(generatedFilename('x'.repeat(200) + '.py').length, 108);
});

test('full-script example contains an explicit replaceable factory and preserved caller', async () => {
  const file = { size: Buffer.byteLength(DEFAULT_SCRIPT), text: async () => DEFAULT_SCRIPT };
  assert.equal(await readObjectiveFile(file), DEFAULT_SCRIPT);
  assert.match(DEFAULT_SCRIPT, /@qatlas.objective\(num_bits=3\)/);
  assert.match(DEFAULT_SCRIPT, /@qatlas.circuit\ndef build_circuit\(\)/);
  assert.match(DEFAULT_SCRIPT, /circuit = build_circuit\(\)/);
});
