import { screen, waitFor, within } from '@testing-library/react';
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

type PaperFixtureOverrides = Partial<{
  id: string;
  projectId: string;
  title: string;
  canonicalTitle: string;
  authors: string[];
  publicationYear: number;
  keywords: string[];
  visibility: 'project_members' | 'group_wide';
  status: string;
  downloadAvailable: boolean;
  defaultDownloadFilename: string;
  viewerAvailable: boolean;
  actionCapabilities: {
    canRename: boolean;
    canDelete: boolean;
    canDownload: boolean;
    canView: boolean;
  };
}>;

function paperFixture(overrides: PaperFixtureOverrides = {}) {
  const canonicalTitle = overrides.canonicalTitle ?? overrides.title ?? 'Graph Neural Methods';
  return {
    id: overrides.id ?? '1',
    projectId: overrides.projectId ?? '7',
    title: overrides.title ?? canonicalTitle,
    canonicalTitle,
    authors: overrides.authors ?? ['Lin Chen'],
    publicationYear: overrides.publicationYear ?? 2026,
    keywords: overrides.keywords ?? ['graph'],
    visibility: overrides.visibility ?? 'group_wide',
    status: overrides.status ?? 'active',
    downloadAvailable: overrides.downloadAvailable ?? true,
    defaultDownloadFilename: overrides.defaultDownloadFilename ?? `${canonicalTitle}.pdf`,
    viewerAvailable: overrides.viewerAvailable ?? true,
    actionCapabilities: overrides.actionCapabilities ?? {
      canRename: false,
      canDelete: false,
      canDownload: overrides.downloadAvailable ?? true,
      canView: true,
    },
  };
}

function mockSharedPaperLibrary(papers = [paperFixture()]) {
  mockFetch((url) => {
    const detail = papers.find((paper) => url.includes(`/api/library/papers/${paper.id}/`));
    if (detail) {
      return detail;
    }
    return { count: papers.length, results: papers };
  });
}

function mockSharedPaperDownload(filename = 'Graph Neural Methods.pdf') {
  return {
    filename,
    deliveryMode: 'direct_response',
  };
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
  it('renders desktop import/download and search/detail areas separately', async () => {
    mockFetch((url) => {
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
      return {
        count: 1,
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
        ],
      };
    });

    renderPaperLibrary();

    const leftArea = await screen.findByRole('region', { name: 'Paper import and download' });
    const rightArea = screen.getByRole('region', { name: 'Shared paper search and display' });

    expect(within(leftArea).getByText('Import paper PDF')).toBeInTheDocument();
    expect(within(leftArea).getByRole('region', { name: 'Selected paper download' })).toBeInTheDocument();
    expect(within(rightArea).getByPlaceholderText('Search title, author, year, keyword')).toBeInTheDocument();
    expect(within(rightArea).getByRole('region', { name: 'Selected paper details' })).toBeInTheDocument();
  });

  it('keeps narrow-screen workflows distinct without metadata fields or lost selection context', async () => {
    mockFetch((url) => {
      if (url.includes('/api/library/papers/2/')) {
        return {
          id: '2',
          projectId: '9',
          title: 'Responsive Reference Systems',
          canonicalTitle: 'Responsive Reference Systems',
          authors: ['Grace Hopper'],
          publicationYear: 2025,
          keywords: ['layout'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Responsive Reference Systems.pdf',
        };
      }
      return {
        count: 1,
        results: [
          {
            id: '2',
            projectId: '9',
            title: 'Responsive Reference Systems',
            canonicalTitle: 'Responsive Reference Systems',
            authors: ['Grace Hopper'],
            publicationYear: 2025,
            keywords: ['layout'],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
            defaultDownloadFilename: 'Responsive Reference Systems.pdf',
          },
        ],
      };
    });

    renderPaperLibrary();

    const workspace = await screen.findByTestId('paper-library-workspace');
    expect(workspace).toHaveClass('grid-cols-1');
    expect(screen.queryByLabelText('Paper title')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Authors')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Publication year')).not.toBeInTheDocument();

    await userEvent.click(await screen.findByRole('button', { name: /Select paper Responsive Reference Systems/ }));

    const leftArea = screen.getByRole('region', { name: 'Paper import and download' });
    expect(within(leftArea).getByText('Responsive Reference Systems')).toBeInTheDocument();
    expect(within(leftArea).getByRole('button', { name: /Download Responsive Reference Systems/ })).toBeEnabled();
  });

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
    expect(screen.getByText('Active filters: Search: missing')).toBeInTheDocument();
    expect(screen.getByText('No shared papers match missing.')).toBeInTheDocument();
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

  it('shows a clear upload-size error when the proxy rejects an oversized PDF', async () => {
    global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/library/papers/') && init?.method === 'POST') {
        return new Response('request entity too large', { status: 413 });
      }
      return new Response(JSON.stringify({ count: 0, results: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch;

    renderPaperLibrary();
    await userEvent.upload(
      screen.getByLabelText('PDF file'),
      new File(['%PDF-1.4'], 'too-large.pdf', { type: 'application/pdf' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Import PDF' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Selected file exceeds the upload size limit.');
  });

  it('shows duplicate imports with an action for the existing paper', async () => {
    mockFetch((url, init) => {
      if (url.includes('/api/library/papers/') && init?.method === 'POST') {
        return {
          id: 'import-duplicate',
          status: 'duplicate',
          requestedBy: '10',
          userMessage: 'Duplicate paper detected.',
          acceptedPaper: null,
          duplicatePaper: {
            id: '3',
            projectId: '12',
            title: 'Existing Deduplicated Paper',
            canonicalTitle: 'Existing Deduplicated Paper',
            authors: ['Ada Lovelace'],
            keywords: [],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
          },
          extraction: {
            source: 'embedded_metadata',
            extractedTitle: 'Different local filename',
            confidence: 'high',
            failureReason: '',
          },
          duplicateDetection: {
            decision: 'duplicate_file_fingerprint',
            matchBasis: 'file_fingerprint',
            candidatePaperId: '3',
            similarityScore: 1,
            reviewStatus: 'none',
          },
          failureReason: 'duplicate',
        };
      }
      if (url.includes('/api/library/papers/3/')) {
        return {
          id: '3',
          projectId: '12',
          title: 'Existing Deduplicated Paper',
          canonicalTitle: 'Existing Deduplicated Paper',
          authors: ['Ada Lovelace'],
          keywords: [],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
        };
      }
      return { count: 0, results: [] };
    });

    renderPaperLibrary();
    await userEvent.upload(
      screen.getByLabelText('PDF file'),
      new File(['%PDF-1.4'], 'renamed.pdf', { type: 'application/pdf' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Import PDF' }));

    expect(await screen.findByText(/Duplicate: Existing Deduplicated Paper/)).toBeInTheDocument();
    expect(screen.getByText('Duplicate paper detected')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View existing paper' })).toBeInTheDocument();
  });

  it('shows fuzzy duplicate imports as maintainer review without accepting a paper', async () => {
    mockFetch((url, init) => {
      if (url.includes('/api/library/papers/') && init?.method === 'POST') {
        return {
          id: 'import-review',
          status: 'maintainer_review',
          requestedBy: '10',
          userMessage: 'Possible duplicate queued for maintainer review.',
          acceptedPaper: null,
          duplicatePaper: {
            id: '4',
            projectId: '12',
            title: 'Graph Neural Methods for Research Groups',
            canonicalTitle: 'Graph Neural Methods for Research Groups',
            authors: ['Ada Lovelace'],
            keywords: [],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
          },
          extraction: {
            source: 'embedded_metadata',
            extractedTitle: 'Graph Neural Method for Research Group',
            confidence: 'high',
            failureReason: '',
          },
          duplicateDetection: {
            decision: 'maintainer_review',
            matchBasis: 'fuzzy_title_metadata',
            candidatePaperId: '4',
            similarityScore: 0.96,
            reviewStatus: 'pending',
          },
          failureReason: '',
        };
      }
      return { count: 0, results: [] };
    });

    renderPaperLibrary();
    await userEvent.upload(
      screen.getByLabelText('PDF file'),
      new File(['%PDF-1.4'], 'fuzzy.pdf', { type: 'application/pdf' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Import PDF' }));

    expect((await screen.findAllByText('Maintainer review required')).length).toBeGreaterThan(0);
    expect(screen.getByText(/Review status: pending/)).toBeInTheDocument();
    expect(screen.queryByText(/Accepted:/)).not.toBeInTheDocument();
  });

  it('renders many papers in a stable scrollable list and opens the selected paper in-page', async () => {
    const papers = Array.from({ length: 18 }, (_, index) =>
      paperFixture({
        id: String(index + 1),
        title: `Scrollable Paper ${index + 1}`,
        canonicalTitle: `Scrollable Paper ${index + 1}`,
        authors: [`Author ${index + 1}`],
      }),
    );
    mockSharedPaperLibrary(papers);

    renderPaperLibrary();

    const list = await screen.findByTestId('paper-results-list');
    expect(list).toHaveClass('overflow-y-auto');
    expect(list).toHaveStyle({ maxHeight: '34rem' });

    await userEvent.click(await screen.findByRole('button', { name: /Open paper Scrollable Paper 14/ }));

    const selectedRow = screen.getByRole('button', { name: /Open paper Scrollable Paper 14/ });
    expect(selectedRow).toHaveAttribute('data-selected', 'true');
    expect(screen.getByRole('region', { name: 'Selected paper details' })).toHaveTextContent(
      'Scrollable Paper 14',
    );
    expect(screen.getByText('In-page viewer')).toBeInTheDocument();
  });

  it('opens a focused paper row with Enter and Space keyboard input', async () => {
    mockSharedPaperLibrary([
      paperFixture({ id: '1', title: 'Keyboard Paper One', canonicalTitle: 'Keyboard Paper One' }),
      paperFixture({ id: '2', title: 'Keyboard Paper Two', canonicalTitle: 'Keyboard Paper Two' }),
    ]);

    renderPaperLibrary();

    const secondRow = await screen.findByRole('button', { name: /Open paper Keyboard Paper Two/ });
    secondRow.focus();
    await userEvent.keyboard('{Enter}');

    expect(secondRow).toHaveAttribute('data-selected', 'true');
    expect(screen.getByRole('region', { name: 'Selected paper details' })).toHaveTextContent(
      'Keyboard Paper Two',
    );

    const firstRow = screen.getByRole('button', { name: /Open paper Keyboard Paper One/ });
    firstRow.focus();
    await userEvent.keyboard(' ');

    expect(firstRow).toHaveAttribute('data-selected', 'true');
    expect(screen.getByRole('region', { name: 'Selected paper details' })).toHaveTextContent(
      'Keyboard Paper One',
    );
  });

  it('allows maintainers to rename a selected paper and updates list and detail context', async () => {
    let currentPaper = paperFixture({
      id: 'rename-1',
      title: 'Original Rename Title',
      canonicalTitle: 'Original Rename Title',
      actionCapabilities: {
        canRename: true,
        canDelete: false,
        canDownload: true,
        canView: true,
      },
    });
    const requests: string[] = [];
    mockFetch((url, init) => {
      requests.push(`${init?.method ?? 'GET'} ${url}`);
      if (url.includes('/api/library/papers/rename-1/') && init?.method === 'PATCH') {
        const payload = JSON.parse(String(init.body));
        expect(payload).toEqual({ newTitle: 'Renamed Library Title', reason: '' });
        currentPaper = {
          ...currentPaper,
          title: 'Renamed Library Title',
          canonicalTitle: 'Renamed Library Title',
          defaultDownloadFilename: 'Renamed Library Title.pdf',
        };
        return currentPaper;
      }
      if (url.includes('/api/library/papers/rename-1/')) {
        return currentPaper;
      }
      return { count: 1, results: [currentPaper] };
    });

    renderPaperLibrary();

    await userEvent.click(await screen.findByRole('button', { name: /Open paper Original Rename Title/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Rename paper' }));
    await userEvent.clear(screen.getByLabelText('New paper title'));
    await userEvent.type(screen.getByLabelText('New paper title'), 'Renamed Library Title');
    await userEvent.click(screen.getByRole('button', { name: 'Save title' }));

    expect(
      await screen.findByRole('button', { name: /Open paper Renamed Library Title/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Selected paper details' })).toHaveTextContent(
      'Renamed Library Title',
    );
    expect(requests.some((request) => request.startsWith('PATCH'))).toBe(true);
  });

  it('hides rename controls for non-maintainers', async () => {
    const paper = paperFixture({
      id: 'rename-denied',
      title: 'No Rename Permission',
      canonicalTitle: 'No Rename Permission',
      actionCapabilities: {
        canRename: false,
        canDelete: false,
        canDownload: true,
        canView: true,
      },
    });
    mockSharedPaperLibrary([paper]);

    renderPaperLibrary();

    await screen.findByRole('button', { name: /Open paper No Rename Permission/ });
    expect(screen.queryByRole('button', { name: 'Rename paper' })).not.toBeInTheDocument();
  });

  it('shows validation errors from failed rename attempts', async () => {
    const maintainerPaper = paperFixture({
      id: 'rename-invalid',
      title: 'Invalid Rename Source',
      canonicalTitle: 'Invalid Rename Source',
      actionCapabilities: {
        canRename: true,
        canDelete: false,
        canDownload: true,
        canView: true,
      },
    });
    mockFetch((url, init) => {
      if (url.includes('/api/library/papers/rename-invalid/') && init?.method === 'PATCH') {
        return {
          status: 400,
          json: { message: 'Paper title is required.' },
        };
      }
      if (url.includes('/api/library/papers/rename-invalid/')) {
        return maintainerPaper;
      }
      return { count: 1, results: [maintainerPaper] };
    });

    renderPaperLibrary();
    await userEvent.click(await screen.findByRole('button', { name: /Open paper Invalid Rename Source/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Rename paper' }));
    await userEvent.clear(screen.getByLabelText('New paper title'));
    await userEvent.click(screen.getByRole('button', { name: 'Save title' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Paper title is required.');
  });

  it('allows maintainers to delete a selected paper after confirmation without restore controls', async () => {
    let papers = [
      paperFixture({
        id: 'delete-1',
        title: 'Delete Candidate Paper',
        canonicalTitle: 'Delete Candidate Paper',
        actionCapabilities: {
          canRename: true,
          canDelete: true,
          canDownload: true,
          canView: true,
        },
      }),
    ];
    const requests: string[] = [];
    mockFetch((url, init) => {
      requests.push(`${init?.method ?? 'GET'} ${url}`);
      if (url.includes('/api/library/papers/delete-1/') && init?.method === 'DELETE') {
        expect(JSON.parse(String(init.body))).toEqual({ reason: 'Duplicate upload' });
        papers = [];
        return { status: 200, json: null };
      }
      const detail = papers.find((paper) => url.includes(`/api/library/papers/${paper.id}/`));
      if (detail) {
        return detail;
      }
      return { count: papers.length, results: papers };
    });

    renderPaperLibrary();

    await userEvent.click(await screen.findByRole('button', { name: /Open paper Delete Candidate Paper/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete paper' }));
    expect(screen.getByText('Delete Delete Candidate Paper')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Delete reason'), 'Duplicate upload');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Open paper Delete Candidate Paper/ })).not.toBeInTheDocument();
    });
    expect(screen.getByText('No shared papers are available yet.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /restore/i })).not.toBeInTheDocument();
    expect(requests.some((request) => request.startsWith('DELETE'))).toBe(true);
  });

  it('hides delete controls for non-maintainers', async () => {
    const paper = paperFixture({
      id: 'delete-denied',
      title: 'No Delete Permission',
      canonicalTitle: 'No Delete Permission',
      actionCapabilities: {
        canRename: false,
        canDelete: false,
        canDownload: true,
        canView: true,
      },
    });
    mockSharedPaperLibrary([paper]);

    renderPaperLibrary();

    await screen.findByRole('button', { name: /Open paper No Delete Permission/ });
    expect(screen.queryByRole('button', { name: 'Delete paper' })).not.toBeInTheDocument();
  });

  it('shows stale unavailable selected papers without restore controls', async () => {
    const paper = paperFixture({
      id: 'stale-deleted',
      title: 'Stale Deleted Paper',
      canonicalTitle: 'Stale Deleted Paper',
      status: 'deleted',
      downloadAvailable: false,
      viewerAvailable: false,
      actionCapabilities: {
        canRename: false,
        canDelete: false,
        canDownload: false,
        canView: false,
      },
    });
    mockSharedPaperLibrary([paper]);

    renderPaperLibrary();

    await screen.findByRole('button', { name: /Open paper Stale Deleted Paper/ });
    expect(screen.getByRole('alert')).toHaveTextContent('This paper is unavailable and cannot be opened.');
    expect(screen.queryByRole('button', { name: /restore/i })).not.toBeInTheDocument();
  });
});
