import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../src/features/auth/AuthProvider';
import { PaperLibraryPage } from '../../src/features/library/PaperLibraryPage';
import { renderWithClient } from './test-utils';

type MockResult =
  | unknown
  | {
      status: number;
      json: unknown;
      headers?: Record<string, string>;
    }
  | {
      status?: number;
      body: BodyInit;
      headers?: Record<string, string>;
    };

function mockFetch(handler: (url: string, init?: RequestInit) => MockResult) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const result = handler(String(input), init);
    if (
      typeof result === 'object' &&
      result !== null &&
      'body' in result
    ) {
      return new Response(result.body, {
        status: result.status ?? 200,
        headers: result.headers ?? {},
      });
    }
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
      headers: {
        'Content-Type': 'application/json',
        ...(
          typeof result === 'object' &&
          result !== null &&
          'headers' in result &&
          result.headers
            ? result.headers
            : {}
        ),
      },
    });
  }) as typeof fetch;
}

type PaperFixtureOverrides = Partial<{
  id: string;
  projectId: string;
  title: string;
  canonicalTitle: string;
  titleSource: string;
  authors: string[];
  venue: string;
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
  const publicationYear = Object.prototype.hasOwnProperty.call(overrides, 'publicationYear')
    ? overrides.publicationYear
    : 2026;
  return {
    id: overrides.id ?? '1',
    projectId: overrides.projectId ?? '7',
    title: overrides.title ?? canonicalTitle,
    canonicalTitle,
    titleSource: overrides.titleSource ?? 'embedded_metadata',
    authors: overrides.authors ?? ['Lin Chen'],
    venue: overrides.venue,
    publicationYear,
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
    body: new Blob(['%PDF-1.4 component'], { type: 'application/pdf' }),
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
    },
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

function renderAuthenticatedPaperLibrary() {
  return renderWithClient(
    <AuthProvider>
      <MemoryRouter initialEntries={['/library/papers']}>
        <Routes>
          <Route path="/library/papers" element={<PaperLibraryPage />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

const longLayoutTitle =
  'A Very Long Academic Paper Title About Compact Shared Library Browsing Rows Metadata Density Responsive Containers and Full Detail Context Preservation';
const longAuthors = [
  'Alexandra Cassandra Researcher',
  'Benjamin Longform Contributor',
  'Charlotte Metadata Specialist',
  'Deepak Responsive Layout Analyst',
  'Elena File Workflow Reviewer',
];
const longVenue =
  'Proceedings of the International Symposium on Extremely Long Journal Names and Responsive Research Operations';

function layoutPapers() {
  return [
    paperFixture({
      id: 'short-layout',
      title: 'Compact Row Patterns',
      canonicalTitle: 'Compact Row Patterns',
      authors: ['Lin Chen'],
      venue: 'UI Systems',
      titleSource: 'embedded_metadata',
    }),
    paperFixture({
      id: 'long-layout',
      title: 'Local PDF Title',
      canonicalTitle: longLayoutTitle,
      authors: longAuthors,
      venue: longVenue,
      keywords: ['layout', 'overflow', 'responsive'],
      titleSource: 'first_page_visible_text',
    }),
    paperFixture({
      id: 'missing-layout',
      title: 'Missing Metadata Paper',
      canonicalTitle: 'Missing Metadata Paper',
      authors: [],
      venue: '',
      publicationYear: undefined,
      keywords: [],
      titleSource: '',
    }),
  ];
}

async function findPaperRow(title: string | RegExp) {
  const row = await screen.findByRole('button', { name: title instanceof RegExp ? title : new RegExp(title) });
  expect(row).toHaveAttribute('data-testid', 'paper-result-row');
  return row;
}

function getSelectedDetailRegion() {
  return screen.getByRole('region', { name: 'Selected paper details' });
}

function getSelectedTitle(region = getSelectedDetailRegion()) {
  return within(region).getByTestId('paper-detail-title');
}

function getPrimaryActionGroups() {
  return screen.getAllByTestId('paper-primary-action-group');
}

function expectNoChineseText(container: HTMLElement) {
  expect(container.textContent ?? '').not.toMatch(/[\u3400-\u9fff]/);
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
    const previewArea = screen.getByRole('region', { name: 'Paper preview' });

    expect(within(leftArea).getByText('Import paper PDF')).toBeInTheDocument();
    expect(within(leftArea).getByRole('region', { name: 'Selected paper download' })).toBeInTheDocument();
    expect(within(rightArea).getByPlaceholderText('Search title, author, year, keyword')).toBeInTheDocument();
    expect(within(rightArea).getByRole('region', { name: 'Selected paper details' })).toBeInTheDocument();
    expect(within(previewArea).getByText('In-page viewer')).toBeInTheDocument();
  });

  it('renders compact row presentation with clamped titles and bounded metadata summaries', async () => {
    mockSharedPaperLibrary(layoutPapers());

    renderPaperLibrary();

    const rows = await screen.findAllByTestId('paper-result-row');
    expect(rows).toHaveLength(3);
    for (const row of rows) {
      expect(row).toHaveClass('min-h-16');
      expect(row).toHaveClass('grid-cols-[minmax(0,1fr)_auto]');
      expect(row).toHaveClass('overflow-hidden');
      expect(within(row).getByTestId('paper-row-title')).toHaveClass('line-clamp-2');
      expect(within(row).getByTestId('paper-row-metadata')).toHaveClass('truncate');
    }

    const missingRow = await findPaperRow(/Missing Metadata Paper/);
    expect(missingRow).toHaveTextContent('Unknown authors');
    expect(missingRow).toHaveTextContent('No year');
    expect(missingRow).toHaveTextContent('shared');
  });

  it('keeps the full selected title in detail when the browsing row title is clamped', async () => {
    mockSharedPaperLibrary(layoutPapers());

    renderPaperLibrary();

    const longRow = await findPaperRow(/A Very Long Academic Paper Title/);
    expect(within(longRow).getByTestId('paper-row-title')).toHaveClass('line-clamp-2');
    await userEvent.click(longRow);

    const detail = getSelectedDetailRegion();
    expect(getSelectedTitle(detail)).toHaveTextContent(longLayoutTitle);
    expect(getSelectedTitle(detail)).not.toHaveClass('line-clamp-2');
    expect(detail).toHaveTextContent(longVenue);
    expect(detail).toHaveTextContent(longAuthors.join(', '));
  });

  it('renders many papers in a bounded vertically scrollable results region without hiding detail context', async () => {
    const papers = Array.from({ length: 32 }, (_, index) =>
      paperFixture({
        id: `bounded-${index + 1}`,
        title: `Bounded Scroll Paper ${index + 1}`,
        canonicalTitle: `Bounded Scroll Paper ${index + 1}`,
        authors: [`Author ${index + 1}`],
      }),
    );
    mockSharedPaperLibrary(papers);

    renderPaperLibrary();

    const list = await screen.findByTestId('paper-results-list');
    expect(list).toHaveClass('max-h-[32rem]');
    expect(list).toHaveClass('overflow-y-auto');
    expect(await screen.findAllByTestId('paper-result-row')).toHaveLength(32);

    await userEvent.click(await findPaperRow(/Bounded Scroll Paper 29/));

    expect(getSelectedTitle()).toHaveTextContent('Bounded Scroll Paper 29');
    expect(screen.getByTestId('paper-preview-panel')).toBeInTheDocument();
  });

  it('keeps selected download context and permitted action groups inside stable layout hooks', async () => {
    const maintainer = paperFixture({
      id: 'maintainer-layout',
      title: longLayoutTitle,
      canonicalTitle: longLayoutTitle,
      authors: longAuthors,
      venue: longVenue,
      actionCapabilities: {
        canRename: true,
        canDelete: true,
        canDownload: true,
        canView: true,
      },
    });
    mockSharedPaperLibrary([maintainer]);

    renderPaperLibrary();

    await userEvent.click(await findPaperRow(/A Very Long Academic Paper Title/));
    expect(getSelectedTitle()).toHaveTextContent(longLayoutTitle);
    for (const group of getPrimaryActionGroups()) {
      expect(group).toHaveClass('min-w-0');
      expect(group).toHaveClass('flex-wrap');
    }
    expect(screen.getByRole('button', { name: 'Rename paper' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete paper' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Download A Very Long Academic Paper Title/ })).toBeEnabled();
  });

  it('shows maintainer rename and delete actions when older paper responses omit action capabilities', async () => {
    const paperWithoutCapabilities = paperFixture({
      id: 'legacy-capabilities',
      title: 'Legacy Capability Paper',
      canonicalTitle: 'Legacy Capability Paper',
    });
    Reflect.deleteProperty(paperWithoutCapabilities, 'actionCapabilities');

    mockFetch((url) => {
      if (url.includes('/api/accounts/me/')) {
        return {
          id: 10,
          email: 'advisor@example.edu',
          name: 'Advisor',
          global_role: 'advisor',
          status: 'active',
        };
      }
      if (url.includes('/api/library/papers/legacy-capabilities/')) {
        return paperWithoutCapabilities;
      }
      return { count: 1, results: [paperWithoutCapabilities] };
    });

    renderAuthenticatedPaperLibrary();

    await userEvent.click(await screen.findByRole('button', { name: /Open paper Legacy Capability Paper/ }));

    expect(screen.getByRole('button', { name: 'Rename paper' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete paper' })).toBeInTheDocument();
  });

  it('uses selected paper detail capabilities when list summaries are stale', async () => {
    const listPaper = paperFixture({
      id: 'detail-capabilities',
      title: 'Detail Capability Paper',
      canonicalTitle: 'Detail Capability Paper',
      actionCapabilities: {
        canRename: false,
        canDelete: false,
        canDownload: true,
        canView: true,
      },
    });
    const detailPaper = {
      ...listPaper,
      actionCapabilities: {
        canRename: true,
        canDelete: true,
        canDownload: true,
        canView: true,
      },
    };

    mockFetch((url) => {
      if (url.includes('/api/accounts/me/')) {
        return {
          id: 10,
          email: 'advisor@example.edu',
          name: 'Advisor',
          global_role: 'advisor',
          status: 'active',
        };
      }
      if (url.includes('/api/library/papers/detail-capabilities/')) {
        return detailPaper;
      }
      return { count: 1, results: [listPaper] };
    });

    renderAuthenticatedPaperLibrary();

    await userEvent.click(await screen.findByRole('button', { name: /Open paper Detail Capability Paper/ }));

    expect(await screen.findByRole('button', { name: 'Rename paper' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete paper' })).toBeInTheDocument();
  });

  it('uses bounded layout state hooks for loading, empty, error, permission, unavailable, and no-paper states', async () => {
    global.fetch = vi.fn(() => new Promise<Response>(() => undefined)) as typeof fetch;
    renderPaperLibrary();
    expect(await screen.findByTestId('paper-layout-state')).toHaveTextContent('Loading papers');

    cleanup();
    mockFetch(() => ({ count: 0, results: [] }));
    renderPaperLibrary();
    await waitFor(() => {
      expect(screen.getByTestId('paper-layout-state')).toHaveTextContent('No shared papers');
    });

    cleanup();
    mockFetch(() => ({ status: 500, json: { message: 'Paper service unavailable.' } }));
    renderPaperLibrary();
    await waitFor(() => {
      expect(screen.getByTestId('paper-layout-state')).toHaveTextContent('Paper library unavailable');
    });

    cleanup();
    mockFetch(() => ({
      status: 403,
      json: { message: 'Active account required for the shared paper library.' },
    }));
    renderPaperLibrary();
    await waitFor(() => {
      expect(screen.getByTestId('paper-layout-state')).toHaveTextContent('Active account required');
    });

    cleanup();
    const unavailable = paperFixture({
      id: 'unavailable-layout',
      title: 'Unavailable Layout Paper',
      canonicalTitle: 'Unavailable Layout Paper',
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
    mockSharedPaperLibrary([unavailable]);
    renderPaperLibrary();
    await waitFor(() => {
      expect(screen.getByTestId('paper-preview-state')).toHaveTextContent('This paper is unavailable');
    });
  });

  it('does not leave restricted maintainer action gaps for non-maintainers', async () => {
    const paper = paperFixture({
      id: 'non-maintainer-layout',
      title: 'Non Maintainer Layout Paper',
      canonicalTitle: 'Non Maintainer Layout Paper',
      actionCapabilities: {
        canRename: false,
        canDelete: false,
        canDownload: true,
        canView: true,
      },
    });
    mockSharedPaperLibrary([paper]);

    renderPaperLibrary();

    await findPaperRow(/Non Maintainer Layout Paper/);
    const detail = getSelectedDetailRegion();
    expect(within(detail).queryByRole('button', { name: 'Rename paper' })).not.toBeInTheDocument();
    expect(within(detail).queryByRole('button', { name: 'Delete paper' })).not.toBeInTheDocument();
    expect(within(detail).getByTestId('paper-primary-action-group')).toHaveClass('flex-wrap');
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
    const createObjectURL = vi.fn(() => 'blob:paper-download');
    const revokeObjectURL = vi.fn();
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    mockFetch((url, init) => {
      requests.push(`${init?.method ?? 'GET'} ${url}`);
      if (url.includes('/api/library/papers/2/download/')) {
        return mockSharedPaperDownload('Neural Collaboration Without Project Scope.pdf');
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
    expect(createObjectURL).toHaveBeenCalled();
    expect(anchorClick).toHaveBeenCalled();
    expect(requests.some((request) => request.includes('/api/library/papers/?'))).toBe(true);
    expect(requests.some((request) => request.includes('/api/library/papers/2/'))).toBe(true);
    anchorClick.mockRestore();
  });

  it('keeps selected-paper download disabled until a paper is selected', async () => {
    mockSharedPaperLibrary([paperFixture({ title: 'Download Later', canonicalTitle: 'Download Later' })]);

    renderPaperLibrary();

    const downloadRegion = await screen.findByRole('region', { name: 'Selected paper download' });
    expect(within(downloadRegion).getByText('Select a paper from the results before downloading.')).toBeInTheDocument();
    expect(within(downloadRegion).getByRole('button', { name: 'Download selected paper' })).toBeDisabled();
  });

  it('shows a recoverable download error when the shared PDF is unavailable', async () => {
    const paper = paperFixture({
      id: 'recoverable',
      title: 'Recoverable Download Paper',
      canonicalTitle: 'Recoverable Download Paper',
    });
    mockFetch((url) => {
      if (url.includes('/api/library/papers/recoverable/download/')) {
        return {
          status: 410,
          json: { message: 'This paper is no longer available.' },
        };
      }
      if (url.includes('/api/library/papers/recoverable/')) {
        return paper;
      }
      return { count: 1, results: [paper] };
    });

    renderPaperLibrary();

    await userEvent.click(await screen.findByRole('button', { name: /Select paper Recoverable Download Paper/ }));
    await userEvent.click(screen.getByRole('button', { name: /Download Recoverable Download Paper/ }));

    await waitFor(() => {
      expect(screen.getAllByText('This paper is no longer available.').length).toBeGreaterThan(0);
    });
  });

  it('renders an empty state tied to the active shared-library search', async () => {
    mockFetch(() => ({ count: 0, results: [] }));

    renderPaperLibrary();
    await userEvent.type(screen.getByPlaceholderText('Search title, author, year, keyword'), 'missing');

    expect(await screen.findByText('No shared papers')).toBeInTheDocument();
    expect(screen.getByText('Active filters: Search: missing')).toBeInTheDocument();
    expect(screen.getByText('No shared papers match missing.')).toBeInTheDocument();
  });

  it('keeps English paper-library render paths free of Chinese characters', async () => {
    const paper = paperFixture({
      id: 'locale-maintainer',
      title: 'English Locale Paper',
      canonicalTitle: 'English Locale Paper',
      actionCapabilities: {
        canRename: true,
        canDelete: true,
        canDownload: true,
        canView: true,
      },
    });
    mockFetch((url, init) => {
      if (url.includes('/api/library/papers/upload-policy/')) {
        return {
          category: 'paper',
          maxSizeBytes: 2 * 1024 * 1024,
          displayLabel: '2 MB',
          allowedExtensions: ['.pdf'],
          contentTypes: ['application/pdf'],
        };
      }
      if (url.includes('/api/library/papers/locale-maintainer/') && init?.method === 'PATCH') {
        return { ...paper, title: 'Renamed Locale Paper', canonicalTitle: 'Renamed Locale Paper' };
      }
      if (url.includes('/api/library/papers/locale-maintainer/') && init?.method === 'DELETE') {
        return { status: 204, json: undefined };
      }
      if (url.includes('/api/library/papers/locale-maintainer/')) {
        return paper;
      }
      return { count: 1, results: [paper] };
    });

    const { container } = renderPaperLibrary();

    await userEvent.click(await screen.findByRole('button', { name: /Open paper English Locale Paper/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Rename paper' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete paper' }));

    expect(screen.getByLabelText('PDF file')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Choose PDFs' })).toBeInTheDocument();
    expect(screen.getByText('The paper will leave ordinary browse, open, and download workflows.')).toBeInTheDocument();
    expectNoChineseText(container);
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
    expect((await screen.findAllByText('Extracted Metadata Title')).length).toBeGreaterThan(0);
  });

  it('imports multiple PDFs sequentially, skips failed files, and contains long filenames within the file list', async () => {
    const postedFiles: string[] = [];
    mockFetch((url, init) => {
      if (url.includes('/api/library/papers/upload-policy/')) {
        return {
          category: 'paper',
          maxSizeBytes: 25 * 1024 * 1024,
          displayLabel: '25 MB',
          allowedExtensions: ['.pdf'],
          contentTypes: ['application/pdf'],
        };
      }
      if (url.includes('/api/library/papers/') && init?.method === 'POST') {
        const body = init.body as FormData;
        const file = body.get('file') as File;
        postedFiles.push(file.name);
        if (file.name.startsWith('a-very-long-local-paper-file-name')) {
          return {
            status: 400,
            json: {
              code: 'invalid_upload',
              message: 'The PDF title could not be extracted.',
            },
          };
        }
        const title = postedFiles.length === 2 ? 'Batch Paper Two' : 'Batch Paper Three';
        return {
          id: `import-${postedFiles.length}`,
          status: 'accepted',
          requestedBy: '10',
          userMessage: 'Paper imported',
          acceptedPaper: {
            id: `batch-${postedFiles.length}`,
            projectId: '12',
            title,
            canonicalTitle: title,
            authors: [],
            keywords: [],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
          },
          duplicatePaper: null,
          extraction: {
            source: 'embedded_metadata',
            extractedTitle: title,
            confidence: 'high',
            failureReason: '',
          },
          duplicateDetection: null,
          failureReason: '',
        };
      }
      return { count: 0, results: [] };
    });

    renderPaperLibrary();
    const longName =
      'a-very-long-local-paper-file-name-that-should-not-stretch-the-import-panel-or-overflow-layout.pdf';
    await userEvent.upload(screen.getByLabelText('PDF file'), [
      new File(['%PDF-1.4'], longName, { type: 'application/pdf' }),
      new File(['%PDF-1.4'], 'second.pdf', { type: 'application/pdf' }),
      new File(['%PDF-1.4'], 'third.pdf', { type: 'application/pdf' }),
    ]);

    expect(screen.getByRole('list', { name: 'Selected PDF files' })).toHaveClass('overflow-y-auto');
    expect(screen.getByText(longName)).toHaveClass('truncate');
    expect(screen.getByText('3 PDFs selected')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clear selected PDFs' })).toHaveClass('min-w-0');
    await userEvent.click(screen.getByRole('button', { name: 'Import PDFs' }));

    await waitFor(() => {
      expect(postedFiles).toEqual([longName, 'second.pdf', 'third.pdf']);
    });
    expect(await screen.findByText(/Accepted: Batch Paper Three/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText(/The PDF title could not be extracted./).length).toBeGreaterThan(0);
    });
    expect(screen.getByText(longName)).toHaveClass('truncate');
  });

  it('clears selected PDF files without stretching the import controls', async () => {
    mockFetch((url) => {
      if (url.includes('/api/library/papers/upload-policy/')) {
        return {
          category: 'paper',
          maxSizeBytes: 25 * 1024 * 1024,
          displayLabel: '25 MB',
          allowedExtensions: ['.pdf'],
          contentTypes: ['application/pdf'],
        };
      }
      return { count: 0, results: [] };
    });

    renderPaperLibrary();
    await userEvent.upload(screen.getByLabelText('PDF file'), [
      new File(['%PDF-1.4'], 'first.pdf', { type: 'application/pdf' }),
      new File(['%PDF-1.4'], 'second.pdf', { type: 'application/pdf' }),
    ]);

    expect(screen.getByRole('list', { name: 'Selected PDF files' })).toBeInTheDocument();
    expect(screen.getByText('2 PDFs selected')).toBeInTheDocument();

    const clearButton = screen.getByRole('button', { name: 'Clear selected PDFs' });
    expect(clearButton).toHaveClass('min-w-0');
    await userEvent.click(clearButton);

    expect(screen.queryByRole('list', { name: 'Selected PDF files' })).not.toBeInTheDocument();
    expect(screen.queryByText('2 PDFs selected')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Clear selected PDFs' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Import PDF' })).toBeDisabled();
  });

  it('shows a clear upload-size error when the proxy rejects an oversized PDF', async () => {
    global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/library/papers/upload-policy/')) {
        return new Response(JSON.stringify({
          category: 'paper',
          maxSizeBytes: 7 * 1024 * 1024,
          displayLabel: '7 MB',
          allowedExtensions: ['.pdf'],
          contentTypes: ['application/pdf'],
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.includes('/api/library/papers/') && init?.method === 'POST') {
        return new Response(JSON.stringify({
          code: 'invalid_upload',
          message: 'The selected PDF exceeds the 7 MB upload size limit.',
          reason: 'oversized',
        }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ count: 0, results: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch;

    renderPaperLibrary();
    expect(await screen.findByText((_, element) => element?.textContent === '.pdf up to 7 MB')).toBeInTheDocument();
    expect(screen.queryByText((_, element) => element?.textContent === '.pdf up to 25 MB')).not.toBeInTheDocument();

    await userEvent.upload(
      screen.getByLabelText('PDF file'),
      new File(['%PDF-1.4'], 'too-large.pdf', { type: 'application/pdf' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Import PDF' }));

    await waitFor(() => {
      expect(screen.getAllByText('too-large.pdf: The selected PDF exceeds the 7 MB upload size limit.').length).toBeGreaterThan(0);
    });
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
    expect(list).toHaveClass('max-h-[32rem]');

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

    await waitFor(() => {
      expect(screen.getAllByText('Paper title is required.').length).toBeGreaterThan(0);
    });
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
    expect(screen.getByTestId('paper-preview-state')).toHaveTextContent('This paper is unavailable and cannot be opened.');
    expect(screen.queryByRole('button', { name: /restore/i })).not.toBeInTheDocument();
  });
});
