import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { CodeRepositoryPage } from '../../src/features/repositories/CodeRepositoryPage';
import { renderWithClient } from './test-utils';

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const payload = handler(String(input), init);
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

function renderCodeRepository() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/projects/1/code']}>
      <Routes>
        <Route path="/projects/:projectId/code" element={<CodeRepositoryPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('collaboration code library UI', () => {
  it('shows archive upload requirements, search, visibility, and download state', async () => {
    mockFetch((url) => {
      if (url.includes('/download')) {
        return { filename: 'analysis.zip', deliveryMode: 'direct_response' };
      }
      return {
        results: [
          {
            id: '3',
            projectId: '1',
            name: 'Analysis Pipeline',
            description: 'Microscopy image analysis archive',
            tags: ['analysis'],
            visibility: 'group_wide',
            checksumSha256: 'c'.repeat(64),
            archiveFileId: '9',
            status: 'active',
          },
        ],
      };
    });

    renderCodeRepository();

    expect(await screen.findByText('Code archive upload')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search name, description, tag')).toBeInTheDocument();
    expect((await screen.findAllByText('Analysis Pipeline')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('group wide').length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: /Download/ }));
    expect(await screen.findByText(/analysis.zip/)).toBeInTheDocument();
  });

  it('uploads a compressed archive with required description', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (init?.method === 'POST' && url.endsWith('/code-artifacts/')) {
        return {
          id: '4',
          projectId: '1',
          name: 'Uploaded Archive',
          description: 'Searchable implementation archive',
          tags: ['python'],
          visibility: 'project_members',
          checksumSha256: 'd'.repeat(64),
          archiveFileId: '10',
          status: 'active',
        };
      }
      return { results: [] };
    });

    renderCodeRepository();
    expect(await screen.findByText('No code artifacts')).toBeInTheDocument();

    await userEvent.upload(
      screen.getByLabelText('Archive file'),
      new File(['zip'], 'uploaded.zip', { type: 'application/zip' }),
    );
    await userEvent.type(screen.getByLabelText('Artifact name'), 'Uploaded Archive');
    await userEvent.type(screen.getByLabelText('Artifact description'), 'Searchable implementation archive');
    await userEvent.click(screen.getByRole('button', { name: 'Upload archive' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
  });
});
