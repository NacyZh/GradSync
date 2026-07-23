import { describe, expect, it } from 'vitest';

import { uploadSizeError, type UploadPolicy } from '../../src/shared/api/uploadPolicy';

const policy: UploadPolicy = {
  category: 'document',
  maxSizeBytes: 7,
  displayLabel: '7 bytes',
  allowedExtensions: ['.pdf'],
  contentTypes: ['application/pdf'],
};

describe('upload policy', () => {
  it('uses backend policy metadata for client-side size validation', () => {
    const valid = new File(['1234567'], 'valid.pdf', { type: 'application/pdf' });
    const oversized = new File(['12345678'], 'oversized.pdf', { type: 'application/pdf' });

    expect(uploadSizeError(valid, policy)).toBe('');
    expect(uploadSizeError(oversized, policy)).toBe(
      'oversized.pdf exceeds the 7 bytes upload size limit.',
    );
  });
});
