import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { PaperLibraryPage } from '../../src/features/library/PaperLibraryPage';
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

function renderPaperLibrary() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/projects/1/papers']}>
      <Routes>
        <Route path="/projects/:projectId/papers" element={<PaperLibraryPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('collaboration paper library UI', () => {
  it('shows upload requirements, filters, visibility, and download state', async () => {
    mockFetch((url, init) => {
      if (init?.method === 'POST' && url.includes('/download/')) {
        return { filename: 'graph.pdf', deliveryMode: 'direct_response' };
      }
      return {
        results: [
          {
            id: '7',
            projectId: '1',
            title: 'Graph Neural Collaboration',
            authors: ['Lin Chen'],
            publicationYear: 2026,
            visibility: 'group_wide',
            status: 'active',
            attachments: [{ id: '11', filename: 'graph.pdf', checksumSha256: 'a'.repeat(64), status: 'active' }],
          },
        ],
      };
    });

    renderPaperLibrary();

    expect(await screen.findByText('PDF paper upload')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search title, author, year, keyword')).toBeInTheDocument();
    expect((await screen.findAllByText('Graph Neural Collaboration')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('group wide').length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: /Download/ }));
    expect(await screen.findByText(/graph.pdf/)).toBeInTheDocument();
  });

  it('uploads a PDF with metadata and renders empty filtered state', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (init?.method === 'POST' && url.endsWith('/papers/')) {
        return {
          id: '8',
          projectId: '1',
          title: 'Uploaded Paper',
          authors: ['Ada'],
          visibility: 'project_members',
          status: 'active',
          attachments: [{ id: '12', filename: 'uploaded.pdf', checksumSha256: 'b'.repeat(64), status: 'active' }],
        };
      }
      return { results: [] };
    });

    renderPaperLibrary();
    expect(await screen.findByText('No papers')).toBeInTheDocument();

    await userEvent.upload(
      screen.getByLabelText('PDF file'),
      new File(['%PDF-1.4'], 'uploaded.pdf', { type: 'application/pdf' }),
    );
    await userEvent.type(screen.getByLabelText('Paper title'), 'Uploaded Paper');
    await userEvent.type(screen.getByLabelText('Authors'), 'Ada');
    await userEvent.click(screen.getByRole('button', { name: 'Upload paper' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
  });
});
