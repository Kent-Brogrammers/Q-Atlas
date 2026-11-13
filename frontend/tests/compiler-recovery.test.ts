import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError } from '../src/api/client.ts';
import {
  HARDWARE_REQUEST_STORAGE_KEY,
  clearMissingHardwareReference,
  isMissingHardwareRequest
} from '../src/compiler/hardware-recovery.ts';

const missing = new ApiError(422, {
  status: 'error',
  error: {
    code: 'VALIDATION_ERROR',
    message: 'Record not found.',
    diagnostics: [
      { code: 'HARDWARE_REQUEST_NOT_FOUND', message: 'Record not found.', severity: 'error' }
    ]
  }
});

test('only an explicit missing-record response enables browser cleanup', () => {
  assert.equal(isMissingHardwareRequest(missing), true);
  for (const error of [
    new Error('not found'),
    undefined,
    new ApiError(503, missing.body),
    new ApiError(422, {
      status: 'error',
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Other rejection',
        diagnostics: []
      }
    })
  ]) {
    assert.equal(isMissingHardwareRequest(error), false);
    assert.throws(() =>
      clearMissingHardwareReference(
        {
          getItem: () => 'old',
          removeItem: () => assert.fail('must retain recovery ID')
        },
        'old',
        error
      )
    );
  }
});

test('explicit cleanup removes only the matching browser reference', () => {
  const values = new Map([
    [HARDWARE_REQUEST_STORAGE_KEY, 'old'],
    ['another-key', 'keep']
  ]);
  clearMissingHardwareReference(
    {
      getItem: (key) => values.get(key) ?? null,
      removeItem: (key) => {
        values.delete(key);
      }
    },
    'old',
    missing
  );
  assert.equal(values.has(HARDWARE_REQUEST_STORAGE_KEY), false);
  assert.equal(values.get('another-key'), 'keep');
});

test('another tab changing the ID or unavailable storage preserves recovery state', () => {
  assert.throws(
    () =>
      clearMissingHardwareReference(
        {
          getItem: () => 'new-request',
          removeItem: () => assert.fail('must preserve the new ID')
        },
        'old',
        missing
      ),
    /changed/
  );
  assert.throws(
    () =>
      clearMissingHardwareReference(
        {
          getItem: () => {
            throw new Error('Storage unavailable');
          },
          removeItem: () => assert.fail('must not remove anything')
        },
        'old',
        missing
      ),
    /Storage unavailable/
  );
});
