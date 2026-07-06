import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { PaperLibraryPage } from '../../src/features/library/PaperLibraryPage';
import { renderWithClient } from './test-utils';

type MockResult =
  | unknown
  | {
      status: number;
      json: unknown;
    };

function mockFetch(handler: (url: string, init?: RequestInit) => MockResult) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const result = handler(String(input), init);
    const status =
      typeof result === 'object' &&
      result !== null &&
      'status' in result &&
      typeof result.status === 'number'
        ? Number(result.status)
        : 200;
    const payload =
      typeof result === 'object' &&
      result !== null &&
      'json' in result &&
      typeof result.status === 'number'
        ? result.json
        : result;
    return new Response(JSON.stringify(payload), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

function renderPaperLibrary() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/library/papers']}>
      <Routes>
        <Route path="/library/papers" element={<PaperLibraryPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('collaboration paper library UI', () => {
  it('searches shared papers, selects detail, and downloads by canonical title', async () => {
    const requests: string[] = [];
    mockFetch((url, init) => {
      requests.push(`${init?.method ?? 'GET'} ${url}`);
      if (url.includes('/api/library/papers/2/download/')) {
        return {
          filename: 'Neural Collaboration Without Project Scope.pdf',
          deliveryMode: 'direct_response',
        };
      }
      if (url.includes('/api/library/papers/1/')) {
        return {
          id: '1',
          projectId: '7',
          title: 'Graph Neural Methods',
          canonicalTitle: 'Graph Neural Methods',
          authors: ['Lin Chen'],
          publicationYear: 2026,
          keywords: ['graph'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Graph Neural Methods.pdf',
        };
      }
      if (url.includes('/api/library/papers/2/')) {
        return {
          id: '2',
          projectId: '9',
          title: 'Neural Collaboration',
          canonicalTitle: 'Neural Collaboration Without Project Scope',
          authors: ['Grace Hopper'],
          publicationYear: 2025,
          keywords: ['collaboration'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Neural Collaboration Without Project Scope.pdf',
        };
      }
      return {
        count: 2,
        results: [
          {
            id: '1',
            projectId: '7',
            title: 'Graph Neural Methods',
            canonicalTitle: 'Graph Neural Methods',
            authors: ['Lin Chen'],
            publicationYear: 2026,
            keywords: ['graph'],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
            defaultDownloadFilename: 'Graph Neural Methods.pdf',
          },
          {
            id: '2',
            projectId: '9',
            title: 'Neural Collaboration',
            canonicalTitle: 'Neural Collaboration Without Project Scope',
            authors: ['Grace Hopper'],
            publicationYear: 2025,
            keywords: ['collaboration'],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
            defaultDownloadFilename: 'Neural Collaboration Without Project Scope.pdf',
          },
        ],
      };
    });

    renderPaperLibrary();

    expect(await screen.findByText('Graph Neural Methods')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search title, author, year, keyword')).toBeInTheDocument();
    expect(screen.queryByText(/Project members/i)).not.toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Search title, author, year, keyword'), 'Neural');
    await userEvent.click(await screen.findByRole('button', { name: /Select paper Neural Collaboration/ }));

    await waitFor(() => {
      expect(screen.getAllByText('Neural Collaboration Without Project Scope').length).toBeGreaterThan(0);
    });
    await userEvent.click(screen.getByRole('button', { name: /Download/ }));

    expect(await screen.findByText(/Neural Collaboration Without Project Scope\.pdf/)).toBeInTheDocument();
    expect(requests.some((request) => request.includes('/api/library/papers/?'))).toBe(true);
    expect(requests.some((request) => request.includes('/api/library/papers/2/'))).toBe(true);
  });

  it('renders an empty state tied to the active shared-library search', async () => {
    mockFetch(() => ({ count: 0, results: [] }));

    renderPaperLibrary();
    await userEvent.type(screen.getByPlaceholderText('Search title, author, year, keyword'), 'missing');

    expect(await screen.findByText('No shared papers')).toBeInTheDocument();
    expect(screen.getByText(/missing/)).toBeInTheDocument();
  });

  it('renders an inactive-account state when shared paper access is forbidden', async () => {
    mockFetch(() => ({
      status: 403,
      json: { message: 'Active account required for the shared paper library.' },
    }));

    renderPaperLibrary();

    await waitFor(() => {
      expect(screen.getByText('Paper library unavailable')).toBeInTheDocument();
    });
    expect(screen.getByText(/Active account required/)).toBeInTheDocument();
  });

  it('imports a paper by file selection only and exposes accepted title state', async () => {
    let imported = false;
    mockFetch((url, init) => {
      if (url.includes('/api/library/papers/') && init?.method === 'POST') {
        const body = init.body as FormData;
        imported = true;
        expect(body.get('file')).toBeInstanceOf(File);
        expect(body.get('title')).toBeNull();
        expect(body.get('authors')).toBeNull();
        expect(body.get('publicationYear')).toBeNull();
        return {
          id: 'import-1',
          status: 'accepted',
          requestedBy: '10',
          userMessage: 'Paper imported',
          acceptedPaper: {
            id: '7',
            projectId: '12',
            title: 'Extracted Metadata Title',
            canonicalTitle: 'Extracted Metadata Title',
            authors: [],
            keywords: [],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
          },
          duplicatePaper: null,
          extraction: {
            source: 'embedded_metadata',
            extractedTitle: 'Extracted Metadata Title',
            confidence: 'high',
            failureReason: '',
          },
          duplicateDetection: null,
          failureReason: '',
          createdAt: '2026-07-06T00:00:00Z',
          updatedAt: '2026-07-06T00:00:02Z',
          completedAt: '2026-07-06T00:00:02Z',
        };
      }
      return {
        count: imported ? 1 : 0,
        results: imported
          ? [
              {
                id: '7',
                projectId: '12',
                title: 'Extracted Metadata Title',
                canonicalTitle: 'Extracted Metadata Title',
                authors: [],
                keywords: [],
                visibility: 'group_wide',
                status: 'active',
                downloadAvailable: true,
              },
            ]
          : [],
      };
    });

    renderPaperLibrary();

    expect(await screen.findByText('Import paper PDF')).toBeInTheDocument();
    expect(screen.queryByLabelText('Paper title')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Authors')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Publication year')).not.toBeInTheDocument();

    await userEvent.upload(
      screen.getByLabelText('PDF file'),
      new File(['%PDF-1.4'], 'local-name.pdf', { type: 'application/pdf' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Import PDF' }));

    expect(await screen.findByText(/Accepted: Extracted Metadata Title/)).toBeInTheDocument();
    expect(await screen.findByText('Extracted Metadata Title')).toBeInTheDocument();
  });
});
