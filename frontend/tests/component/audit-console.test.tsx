import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuditConsolePage } from '../../src/features/admin/AuditConsolePage';
import { renderWithClient } from './test-utils';

describe('audit console', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('renders a bounded list and separate event detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        if (String(url).includes('/audit-events/1')) {
          return new Response(
            JSON.stringify({
              id: 1,
              eventType: 'project_governance.changed',
              summary: 'Ownership transferred',
              category: 'project_governance',
              outcome: 'succeeded',
              actorSnapshot: { name: 'Administrator' },
              targetSnapshot: { status: 'normal' },
              capabilities: { canExport: true },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(
          JSON.stringify({
            results: [{
              id: 1,
              eventType: 'project_governance.changed',
              summary: 'Ownership transferred',
              category: 'project_governance',
              outcome: 'succeeded',
              createdAt: '2026-07-24T00:00:00Z',
            }],
            nextCursor: null,
            capabilities: { canExport: true },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }),
    );

    renderWithClient(
      <MemoryRouter>
        <AuditConsolePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Ownership transferred')).toBeInTheDocument();
    expect(await screen.findByRole('region', { name: 'Audit event detail' })).toBeInTheDocument();
  });
});
