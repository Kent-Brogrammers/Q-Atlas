import assert from 'node:assert/strict';
import { test } from 'node:test';
import { MAX_SOURCE_LENGTH, readObjectiveFile } from '../src/compiler/source.ts';

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
