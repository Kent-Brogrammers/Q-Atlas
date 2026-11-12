import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError } from '../src/api/client.ts';
import { compilerErrorMessage } from '../src/compiler/errors.ts';

test('hardware request validation includes the rejected field in the displayed error', () => {
  const error = new ApiError(422, {
    status: 'error',
    error: {
      code: 'VALIDATION_ERROR',
      message: 'Request validation failed.',
      diagnostics: [
        { code: 'uuid_parsing', message: 'body.request_id: invalid value', severity: 'error' }
      ]
    }
  });
  assert.equal(
    compilerErrorMessage(error, 'Hardware request failed.'),
    'Request validation failed.\nbody.request_id: invalid value'
  );
});

test('actionable hardware rejection is displayed once when also present in diagnostics', () => {
  const message = 'Use Check hardware job, then Start a new hardware test.';
  const error = new ApiError(422, {
    status: 'error',
    error: {
      code: 'VALIDATION_ERROR',
      message,
      diagnostics: [{ code: 'HARDWARE_REQUEST_CONFLICT', message, severity: 'error' }]
    }
  });
  assert.equal(compilerErrorMessage(error, 'Hardware request failed.'), message);
  assert.equal(compilerErrorMessage(new Error('Network failed.'), 'Fallback'), 'Network failed.');
  assert.equal(compilerErrorMessage(undefined, 'Fallback'), 'Fallback');
});
