import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DraftVersionHistory } from '../../src/features/submissions/DraftVersionHistory';
import { ReviewStatusControl } from '../../src/features/submissions/ReviewStatusControl';
import { renderWithClient } from './test-utils';

describe('submission review UI', () => {
  it('renders draft versions', () => {
    renderWithClient(<DraftVersionHistory versions={[{ id: 1, versionNumber: 1, reviewStatus: 'pending_review' }]} />);
    expect(screen.getByText(/Version 1/)).toBeInTheDocument();
  });

  it('renders review status control', () => {
    renderWithClient(<ReviewStatusControl status="pending_review" />);
    expect(screen.getByLabelText('Review status')).toBeInTheDocument();
  });
});
