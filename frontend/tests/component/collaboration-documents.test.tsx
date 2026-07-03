import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { DocumentLibraryPage } from '../../src/features/library/DocumentLibraryPage';
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

function renderDocuments() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/projects/1/documents']}>
      <Routes>
        <Route path="/projects/:projectId/documents" element={<DocumentLibraryPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('collaboration document library UI', () => {
  it('shows category browser, document filters, visibility, and download state', async () => {
    mockFetch((url) => {
      if (url.includes('/download')) {
        return { filename: 'protocol.pdf', deliveryMode: 'direct_response' };
      }
      if (url.includes('/document-categories')) {
        return [
          { id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' },
          { id: '2', name: 'Reports', description: 'Research reports', status: 'active' },
        ];
      }
      return {
        results: [{
          id: '4',
          projectId: '1',
          categoryId: '1',
          categoryName: 'Protocols',
          title: 'Microscope Protocol',
          description: 'Calibration workflow',
          visibility: 'group_wide',
          uploaderId: '10',
          checksumSha256: 'a'.repeat(64),
          createdAt: '2026-07-03T08:00:00Z',
          status: 'active',
        }],
      };
    });

    renderDocuments();

    expect((await screen.findAllByText('Protocols')).length).toBeGreaterThan(0);
    expect(screen.getByPlaceholderText('Search title, category, description')).toBeInTheDocument();
    expect((await screen.findAllByText('Microscope Protocol')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('group wide').length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: /Download/ }));
    expect(await screen.findByText(/protocol.pdf/)).toBeInTheDocument();
  });

  it('uploads a categorized document and distinguishes empty states', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (url.includes('/document-categories')) {
        return [{ id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' }];
      }
      if (init?.method === 'POST' && url.endsWith('/documents')) {
        return {
          id: '5',
          projectId: '1',
          categoryId: '1',
          categoryName: 'Protocols',
          title: 'Uploaded Protocol',
          description: 'Shared instructions',
          visibility: 'project_members',
          uploaderId: '10',
          checksumSha256: 'b'.repeat(64),
          createdAt: '2026-07-03T08:00:00Z',
          status: 'active',
        };
      }
      return { results: [] };
    });

    renderDocuments();
    expect(await screen.findByText('No documents')).toBeInTheDocument();

    await userEvent.upload(
      screen.getByLabelText('Document file'),
      new File(['# protocol'], 'uploaded.md', { type: 'text/markdown' }),
    );
    await userEvent.type(screen.getByLabelText('Document title'), 'Uploaded Protocol');
    await userEvent.selectOptions(screen.getByLabelText('Document category'), '1');
    await userEvent.type(screen.getByLabelText('Document description'), 'Shared instructions');
    await userEvent.click(screen.getByRole('button', { name: 'Upload document' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
    expect(await screen.findByText('Upload complete')).toBeInTheDocument();
  });
});
