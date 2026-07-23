import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { DocumentLibraryPage } from '../../src/features/library/DocumentLibraryPage';
import { CodeRepositoryPage } from '../../src/features/repositories/CodeRepositoryPage';
import { renderWithClient } from './test-utils';

const categories = [{ id: '1', name: 'Protocols', description: '', status: 'active' }];

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const payload = handler(String(input), init);
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

describe('standalone shared asset sections', () => {
  it('uses shared document capabilities for rename and download actions', async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    const sharedDocument = {
      id: 'doc-1',
      projectId: '1',
      categoryId: '1',
      categoryName: 'Protocols',
      title: 'Shared Protocol',
      description: 'Reusable protocol',
      visibility: 'group_wide',
      uploaderId: '2',
      documentFileId: '44',
      checksumSha256: 'a'.repeat(64),
      createdAt: '2026-07-03T08:00:00Z',
      status: 'active',
      actionCapabilities: {
        canView: true,
        canDownload: true,
        canRename: true,
        canDelete: true,
        canUploadGroupWide: true,
      },
    };
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.includes('/document-categories')) return categories;
      if (init?.method === 'PATCH') return { ...sharedDocument, title: 'Renamed Shared Protocol' };
      return { count: 1, results: [sharedDocument] };
    });

    renderWithClient(
      <MemoryRouter initialEntries={['/library/documents']}>
        <Routes>
          <Route path="/library/documents" element={<DocumentLibraryPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId('document-selected-detail-region')).toHaveTextContent('Shared Protocol'));
    expect(screen.getByRole('button', { name: 'Download Shared Protocol' })).toBeEnabled();
    await userEvent.click(screen.getByRole('button', { name: 'Rename document' }));
    await userEvent.clear(screen.getByLabelText('New document title'));
    await userEvent.type(screen.getByLabelText('New document title'), 'Renamed Shared Protocol');
    await userEvent.click(screen.getByRole('button', { name: 'Save title' }));

    await waitFor(() =>
      expect(screen.getByTestId('document-selected-detail-region')).toHaveTextContent('Renamed Shared Protocol'),
    );
    expect(
      requests.some(
        (request) =>
          request.url.endsWith('/api/library/documents/doc-1/')
          && request.init?.method === 'PATCH',
      ),
    ).toBe(true);
  });

  it('hides document visibility controls and uploads through /api/library/documents/', async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.includes('/document-categories')) return categories;
      if (init?.method === 'POST') {
        return {
          id: 'doc-2',
          projectId: '1',
          categoryId: '1',
          categoryName: 'Protocols',
          title: 'Uploaded Shared Protocol',
          visibility: 'group_wide',
          status: 'active',
          actionCapabilities: { canView: true, canDownload: true, canRename: false, canDelete: false, canUploadGroupWide: false },
        };
      }
      return { results: [] };
    });

    renderWithClient(
      <MemoryRouter initialEntries={['/library/documents']}>
        <Routes>
          <Route path="/library/documents" element={<DocumentLibraryPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByTestId('document-library-workspace')).toBeInTheDocument();
    expect(screen.queryByLabelText('Document visibility')).not.toBeInTheDocument();
    await userEvent.upload(
      screen.getByLabelText('Document file'),
      new File(['shared'], 'shared.md', { type: 'text/markdown' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Upload document' }));

    await waitFor(() =>
      expect(requests.some((request) => request.url.endsWith('/api/library/documents/'))).toBe(true),
    );
    const uploadRequest = requests.find((request) => request.init?.method === 'POST');
    expect((uploadRequest?.init?.body as FormData).has('visibility')).toBe(false);
  });

  it('hides code visibility controls and uploads through /api/library/code/', async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.endsWith('/api/code-artifacts/upload-policy/')) {
        return {
          category: 'code',
          maxSizeBytes: 1048576,
          displayLabel: '1 MB',
          allowedExtensions: ['.zip'],
          contentTypes: ['application/zip'],
        };
      }
      if (init?.method === 'POST') {
        return {
          id: 'code-2',
          projectId: '1',
          name: 'Uploaded Shared Code',
          description: 'Reusable code',
          visibility: 'group_wide',
          status: 'active',
          actionCapabilities: { canView: true, canDownload: true, canRename: false, canDelete: false },
        };
      }
      return { results: [] };
    });

    renderWithClient(
      <MemoryRouter initialEntries={['/library/code']}>
        <Routes>
          <Route path="/library/code" element={<CodeRepositoryPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('No code artifacts')).toBeInTheDocument();
    expect(screen.queryByLabelText('Code archive visibility')).not.toBeInTheDocument();
    await userEvent.upload(
      screen.getByLabelText('Archive file'),
      new File(['zip'], 'shared.zip', { type: 'application/zip' }),
    );
    await userEvent.type(screen.getByLabelText('Artifact name'), 'Uploaded Shared Code');
    await userEvent.type(screen.getByLabelText('Artifact description'), 'Reusable code');
    await userEvent.click(screen.getByRole('button', { name: 'Upload archive' }));

    await waitFor(() =>
      expect(requests.some((request) => request.url.endsWith('/api/library/code/'))).toBe(true),
    );
    const uploadRequest = requests.find((request) => request.init?.method === 'POST');
    expect((uploadRequest?.init?.body as FormData).has('visibility')).toBe(false);
  });
});
