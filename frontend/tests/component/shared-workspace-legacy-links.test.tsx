import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { LegacyBoundaryGuidance } from '../../src/shared/ui/LegacyBoundaryGuidance';
import { renderWithClient } from './test-utils';

describe('legacy boundary guidance', () => {
  it('shows accessible moved guidance without private metadata', () => {
    renderWithClient(
      <MemoryRouter>
        <LegacyBoundaryGuidance
          mode="guidance"
          targetPath="/writing"
          message="Writing now uses participant access in the standalone writing workspace."
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole('region', { name: 'Moved workspace guidance' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open workspace' })).toHaveAttribute('href', '/writing');
    expect(screen.queryByText('Private Thesis Title')).not.toBeInTheDocument();
  });

  it('does not link denied users into hidden project material metadata', () => {
    renderWithClient(
      <MemoryRouter>
        <LegacyBoundaryGuidance
          mode="denied"
          targetPath="/library/documents"
          message="Open the standalone shared section. Private project material details are hidden."
        />
      </MemoryRouter>,
    );

    expect(screen.getByText('Workspace access limited')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Open workspace' })).not.toBeInTheDocument();
    expect(screen.queryByText('Project-only Protocol')).not.toBeInTheDocument();
  });
});
