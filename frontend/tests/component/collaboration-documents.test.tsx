import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { DocumentLibraryPage } from '../../src/features/library/DocumentLibraryPage';
import { renderWithClient } from './test-utils';

type MockResponse = {
  status?: number;
  json?: unknown;
};

const categories = [
  { id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' },
  { id: '2', name: 'Reports', description: 'Research reports', status: 'active' },
];

const baseDocument = {
  id: '4',
  projectId: '1',
  categoryId: '1',
  categoryName: 'Protocols',
  title: 'Microscope Protocol',
  description: 'Calibration workflow',
  visibility: 'group_wide' as const,
  uploaderId: '10',
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

function mockFetch(handler: (url: string, init?: RequestInit) => unknown | MockResponse) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const payload = handler(String(input), init);
    if (payload instanceof Response) {
      return payload;
    }
    const response = payload as MockResponse;
    const status =
      response && typeof response === 'object' && 'status' in response && typeof response.status === 'number'
        ? response.status
        : 200;
    const json = response && typeof response === 'object' && 'json' in response ? response.json : payload;
    return new Response(status === 204 ? null : JSON.stringify(json), {
      status,
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
  it('shows the upload limit returned by the active environment policy', async () => {
    mockFetch((url) => {
      if (url.includes('/api/upload-policies/document/')) {
        return {
          category: 'document',
          maxSizeBytes: 7 * 1024 * 1024,
          displayLabel: '7 MB',
          allowedExtensions: ['.pdf', '.docx'],
          contentTypes: [],
        };
      }
      if (url.includes('/document-categories')) return categories;
      return { results: [baseDocument] };
    });

    renderDocuments();

    expect(await screen.findByText('.pdf, .docx up to 7 MB')).toBeInTheDocument();
    expect(screen.queryByText(/up to 50 MB/)).not.toBeInTheDocument();
  });

  it('uses papers-style upload/download and search/display regions', async () => {
    const createObjectURL = vi.fn(() => 'blob:document-download');
    const revokeObjectURL = vi.fn();
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    mockFetch((url) => {
      if (url.includes('/download')) {
        return new Response(new Blob(['document']), {
          status: 200,
          headers: { 'Content-Disposition': 'attachment; filename="protocol.pdf"' },
        });
      }
      if (url.includes('/document-categories')) {
        return categories;
      }
      return { results: [baseDocument] };
    });

    renderDocuments();

    expect(await screen.findByTestId('document-library-workspace')).toBeInTheDocument();
    expect(screen.getByLabelText('Document library upload and download region')).toBeInTheDocument();
    expect(screen.getByLabelText('Document library search and display region')).toBeInTheDocument();
    expect(screen.getByText('Categorized document upload')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Selected document download' })).toHaveTextContent('Microscope Protocol'),
    );
    expect(screen.getByPlaceholderText('Search title, category, description')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Category Protocols' })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId('document-selected-detail-region')).toHaveTextContent('Microscope Protocol'),
    );
    expect(screen.getByRole('button', { name: /Select document Microscope Protocol/ })).toHaveAttribute('aria-pressed', 'true');

    await userEvent.click(screen.getByRole('button', { name: /Download Microscope Protocol/ }));
    expect(await screen.findByText(/protocol.pdf/)).toBeInTheDocument();
    expect(createObjectURL).toHaveBeenCalled();
    expect(anchorClick).toHaveBeenCalled();
  });

  it('uses the shared category selector for list filtering and upload destination', async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.includes('/document-categories')) {
        return categories;
      }
      if (init?.method === 'POST' && url.endsWith('/documents')) {
        return {
          ...baseDocument,
          id: '5',
          title: 'Uploaded Protocol',
          visibility: 'project_members',
        };
      }
      const category = new URL(url, 'http://localhost').searchParams.get('categoryId');
      return { results: category === '2' ? [] : [baseDocument] };
    });

    renderDocuments();

    await userEvent.click(await screen.findByRole('button', { name: 'Category Reports' }));
    await waitFor(() =>
      expect(requests.some((request) => request.url.includes('categoryId=2'))).toBe(true),
    );
    expect(await screen.findByText('No documents in category')).toBeInTheDocument();

    await userEvent.upload(
      screen.getByLabelText('Document file'),
      new File(['# protocol'], 'uploaded.md', { type: 'text/markdown' }),
    );
    expect(screen.getByText(/Selected document: uploaded\.md/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Upload document' }));

    await waitFor(() => expect(requests.some((request) => request.init?.method === 'POST')).toBe(true));
    expect(await screen.findByText('Upload complete')).toBeInTheDocument();
  });

  it('adds a target location and keeps many category tabs in a fixed horizontal strip', async () => {
    const manyCategories = Array.from({ length: 10 }, (_, index) => ({
      id: String(index + 1),
      name: `Location ${index + 1}`,
      description: '',
      status: 'active',
    }));
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.includes('/document-categories') && init?.method === 'POST') {
        return {
          id: '11',
          name: 'Datasets',
          description: 'Experiment datasets',
          status: 'active',
        };
      }
      if (url.endsWith('/document-categories/11') && init?.method === 'DELETE') {
        return { status: 204 };
      }
      if (url.includes('/document-categories')) return manyCategories;
      return { results: [baseDocument] };
    });

    renderDocuments();

    const categoryStrip = await screen.findByTestId('document-category-strip');
    const categoryActions = await screen.findByTestId('document-category-actions');
    expect(categoryStrip).toHaveClass('h-12', 'overflow-x-auto', 'overflow-y-hidden');
    expect(within(categoryStrip).queryByRole('button', { name: 'Add target location' })).not.toBeInTheDocument();
    expect(within(categoryStrip).queryByRole('button', { name: 'Delete target location' })).not.toBeInTheDocument();
    expect(within(categoryActions).getByRole('button', { name: 'Add target location' })).toBeInTheDocument();
    expect(within(categoryActions).getByRole('button', { name: 'Delete target location' })).toBeInTheDocument();
    await screen.findByRole('button', { name: 'Category Location 1' });
    await userEvent.click(screen.getByRole('button', { name: 'Add target location' }));
    await userEvent.type(screen.getByLabelText('Target location name'), 'Datasets');
    await userEvent.type(screen.getByLabelText('Target location description'), 'Experiment datasets');
    await userEvent.click(screen.getByRole('button', { name: 'Add location' }));

    expect(await screen.findByRole('button', { name: 'Category Datasets' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByText('Destination: Datasets')).toBeInTheDocument();
    const createRequest = requests.find(
      (request) => request.url.includes('/document-categories') && request.init?.method === 'POST',
    );
    expect(JSON.parse(String(createRequest?.init?.body))).toEqual({
      name: 'Datasets',
      description: 'Experiment datasets',
    });

    await userEvent.click(screen.getByRole('button', { name: 'Delete target location' }));
    expect(screen.getByText('Delete target location Datasets?')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
    await waitFor(() =>
      expect(
        requests.some(
          (request) => request.url.endsWith('/document-categories/11') && request.init?.method === 'DELETE',
        ),
      ).toBe(true),
    );
    expect(screen.queryByRole('button', { name: 'Category Datasets' })).not.toBeInTheDocument();
    expect(await screen.findByText('Target location deleted')).toBeInTheDocument();
  });

  it('keeps long document rows bounded and shows no-selection download state', async () => {
    const longTitle = 'Document title with exceptionally long protocol naming for responsive layout validation';
    mockFetch((url) => {
      if (url.includes('/document-categories')) {
        return categories;
      }
      return {
        results: [{
          ...baseDocument,
          id: 'long',
          title: longTitle,
          description: 'Long document description '.repeat(24),
          categoryName: 'Very long methods and laboratory safety category',
        }],
      };
    });

    renderDocuments();

    await waitFor(() => expect(screen.getByTestId('document-results-list')).toHaveTextContent(longTitle));
    await waitFor(() =>
      expect(
        within(screen.getByTestId('document-results-list')).getByText((_, element) => element?.textContent === longTitle),
      ).toHaveClass('break-words'),
    );
    expect(screen.getByTestId('document-results-list')).toHaveClass('overflow-x-hidden');
    expect(screen.getByRole('region', { name: 'Selected document download' })).toHaveTextContent(longTitle);
  });

  it('keeps upload available when there are no categories or documents', async () => {
    mockFetch((url) => {
      if (url.includes('/document-categories')) {
        return [];
      }
      return { results: [] };
    });

    renderDocuments();

    expect(await screen.findByText('No target locations')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Selected document download' })).toHaveTextContent('No document selected');
    expect(screen.getByRole('button', { name: 'Choose file' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upload document' })).toBeDisabled();
  });

  it('supports clear and reselect, optional title, and maintainer-only group-wide upload control', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (url.includes('/document-categories')) {
        return categories;
      }
      if (init?.method === 'POST') {
        return {
          ...baseDocument,
          id: 'uploaded',
          title: 'uploaded.md',
          visibility: 'group_wide',
        };
      }
      return { results: [baseDocument] };
    });

    renderDocuments();

    await waitFor(() => expect(screen.getByLabelText('Document visibility')).toBeInTheDocument());
    const fileInput = screen.getByLabelText('Document file');
    await userEvent.upload(fileInput, new File(['old'], 'old.md', { type: 'text/markdown' }));
    expect(screen.getByText(/Selected document: old\.md/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Clear selected file' }));
    expect(screen.queryByText(/Selected document: old\.md/)).not.toBeInTheDocument();

    await userEvent.upload(fileInput, new File(['new'], 'uploaded.md', { type: 'text/markdown' }));
    await userEvent.selectOptions(screen.getByLabelText('Document visibility'), 'group_wide');
    await userEvent.click(screen.getByRole('button', { name: 'Upload document' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
    const uploadRequest = requests.find((request) => request.method === 'POST');
    const formData = uploadRequest?.body as FormData;
    expect(formData.get('file')).toBeInstanceOf(File);
    expect(formData.get('categoryId')).toBe('1');
    expect(formData.get('visibility')).toBe('group_wide');
    expect(formData.has('title')).toBe(false);
  });

  it('hides group-wide upload control for non-maintainer document responses', async () => {
    mockFetch((url) => {
      if (url.includes('/document-categories')) {
        return categories;
      }
      return {
        results: [{
          ...baseDocument,
          actionCapabilities: {
            canView: true,
            canDownload: true,
            canRename: false,
            canDelete: false,
            canUploadGroupWide: false,
          },
        }],
      };
    });

    renderDocuments();

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Select document Microscope Protocol/ })).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText('Document visibility')).not.toBeInTheDocument();
    expect(screen.queryByTestId('document-category-actions')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Add target location' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete target location' })).not.toBeInTheDocument();
  });

  it('supports maintainer rename and delete while syncing selected/list/download state', async () => {
    let documents = [
      baseDocument,
      {
        ...baseDocument,
        id: 'delete-me',
        title: 'Delete Candidate',
      },
    ];
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.includes('/document-categories')) {
        return categories;
      }
      if (init?.method === 'PATCH') {
        const renamed = { ...documents[0], title: 'Renamed Protocol' };
        documents = [renamed, documents[1]];
        return renamed;
      }
      if (init?.method === 'DELETE') {
        documents = documents.filter((document) => document.id !== 'delete-me');
        return { status: 204 };
      }
      return { results: documents };
    });

    renderDocuments();

    await waitFor(() => expect(screen.getByTestId('document-selected-detail-region')).toHaveTextContent('Microscope Protocol'));
    await userEvent.click(screen.getByRole('button', { name: 'Rename document' }));
    await userEvent.clear(screen.getByLabelText('New document title'));
    await userEvent.type(screen.getByLabelText('New document title'), 'Renamed Protocol');
    await userEvent.click(screen.getByRole('button', { name: 'Save title' }));

    await waitFor(() => expect(screen.getByTestId('document-selected-detail-region')).toHaveTextContent('Renamed Protocol'));
    expect(screen.getByRole('region', { name: 'Selected document download' })).toHaveTextContent('Renamed Protocol');
    expect(screen.getByTestId('document-results-list')).toHaveTextContent('Renamed Protocol');
    expect(requests.some((request) => request.init?.method === 'PATCH')).toBe(true);

    await userEvent.click(screen.getByRole('button', { name: /Select document Delete Candidate/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete document' }));
    expect(screen.getByText(/Delete Delete Candidate/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));

    await waitFor(() => expect(screen.queryByText('Delete Candidate')).not.toBeInTheDocument());
    expect(screen.getByTestId('document-selected-detail-region')).toHaveTextContent('Renamed Protocol');
    expect(requests.some((request) => request.init?.method === 'DELETE')).toBe(true);
  });

  it('hides rename and delete controls for non-maintainer documents', async () => {
    mockFetch((url) => {
      if (url.includes('/document-categories')) {
        return categories;
      }
      return {
        results: [{
          ...baseDocument,
          actionCapabilities: {
            canView: true,
            canDownload: true,
            canRename: false,
            canDelete: false,
            canUploadGroupWide: false,
          },
        }],
      };
    });

    renderDocuments();

    await waitFor(() => expect(screen.getByTestId('document-selected-detail-region')).toHaveTextContent('Microscope Protocol'));
    expect(screen.queryByRole('button', { name: 'Rename document' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete document' })).not.toBeInTheDocument();
  });

  it('shows recoverable selected-download errors without losing document context', async () => {
    mockFetch((url) => {
      if (url.includes('/download')) {
        return { status: 410, json: { message: 'Document is no longer available' } };
      }
      if (url.includes('/document-categories')) {
        return categories;
      }
      return { results: [baseDocument] };
    });

    renderDocuments();

    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Selected document download' })).toHaveTextContent('Microscope Protocol'),
    );
    await userEvent.click(screen.getByRole('button', { name: /Download Microscope Protocol/ }));

    await waitFor(() => {
      expect(screen.getAllByText('Document is no longer available').length).toBeGreaterThan(0);
    });
    expect(screen.getByRole('region', { name: 'Selected document download' })).toHaveTextContent('Microscope Protocol');
  });
});
