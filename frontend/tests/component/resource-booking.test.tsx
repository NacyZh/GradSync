import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { BookingConflictAlert } from '../../src/features/resources/BookingConflictAlert';
import { ResourceListPage } from '../../src/features/resources/ResourceListPage';
import { renderWithClient } from './test-utils';

describe('resource booking UI', () => {
  it('renders resources shell', () => {
    renderWithClient(<ResourceListPage />);
    expect(screen.getByText('Lab resources')).toBeInTheDocument();
  });

  it('renders conflict message', () => {
    renderWithClient(<BookingConflictAlert message="Unavailable" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Unavailable');
  });
});
