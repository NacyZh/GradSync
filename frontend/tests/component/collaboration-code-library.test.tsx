import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { CodeRepositoryPage } from '../../src/features/repositories/CodeRepositoryPage';
import { renderWithClient } from './test-utils';

type MockResponse = {
  status?: number;
  json?: unknown;
};

const baseArtifact = {
  id: '3',
  projectId: '1',
  name: 'Analysis Pipeline',
  description: 'Microscopy image analysis archive',
  tags: ['analysis'],
  visibility: 'group_wide' as const,
  checksumSha256: 'c'.repeat(64),
  archiveFileId: '9',
  status: 'active',
  actionCapabilities: {
    canView: true,
    canDownload: true,
    canRename: false,
    canDelete: false,
  },
  latestVersion: {
    id: 'version-3',
    artifactId: '3',
    projectId: '1',
    versionLabel: 'v1',
    filename: 'analysis.zip',
    checksumSha256: 'c'.repeat(64),
    status: 'active',
  },
};

const codeUploadPolicy = {
  category: 'code',
  maxSizeBytes: 100 * 1024 * 1024,
  displayLabel: '100 MB',
  allowedExtensions: ['.7z', '.bz2', '.gz', '.tar', '.tgz', '.xz', '.zip'],
  contentTypes: ['application/zip', 'application/gzip', 'application/x-gzip', 'application/x-tar', 'application/octet-stream'],
};

function mockFetch(handler: (url: string, init?: RequestInit) => unknown | MockResponse) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const payload = url.endsWith('/api/code-artifacts/upload-policy/') ? codeUploadPolicy : handler(url, init);
    if (payload instanceof Response) {
      return payload;
    }
    const response = payload as MockResponse;
    const status = response && typeof response === 'object' && 'status' in response ? (response.status ?? 200) : 200;
    const json = response && typeof response === 'object' && 'json' in response ? response.json : payload;
    return new Response(status === 204 ? null : JSON.stringify(json), {
      status,
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

function renderSharedCodeRepository() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/library/code']}>
      <Routes>
        <Route path="/library/code" element={<CodeRepositoryPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('collaboration code library UI', () => {
  it('shows archive upload requirements, search, visibility, and download state', async () => {
    const createObjectURL = vi.fn(() => 'blob:code-download');
    const revokeObjectURL = vi.fn();
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    mockFetch((url) => {
      if (url.includes('/download')) {
        return new Response(new Blob(['zip']), {
          status: 200,
          headers: { 'Content-Disposition': 'attachment; filename="analysis.zip"' },
        });
      }
      return {
        results: [baseArtifact],
      };
    });

    renderCodeRepository();

    expect(await screen.findByText('Code archive upload')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search name, description, tag')).toBeInTheDocument();
    expect((await screen.findAllByText('Analysis Pipeline')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('group wide').length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: /Download/ }));
    expect((await screen.findAllByText(/analysis.zip/)).length).toBeGreaterThan(0);
    expect(createObjectURL).toHaveBeenCalled();
    expect(anchorClick).toHaveBeenCalled();
  });

  it('uses papers-style layout regions and selects the first artifact by default', async () => {
    mockFetch(() => ({
      results: [
        baseArtifact,
        {
          ...baseArtifact,
          id: '4',
          name: 'Model Training Utilities',
          description: 'Training helpers and scripts',
          archiveFileId: '10',
          latestVersion: { ...baseArtifact.latestVersion, id: 'version-4', artifactId: '4', filename: 'training.zip' },
        },
      ],
    }));

    renderCodeRepository();

    expect(await screen.findByTestId('code-repository-workspace')).toBeInTheDocument();
    expect(screen.getByLabelText('Code repository upload and download region')).toBeInTheDocument();
    expect(screen.getByLabelText('Code repository search and display region')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('code-selected-download-region')).toHaveTextContent('Analysis Pipeline'));
    expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Analysis Pipeline');
    expect(screen.getByRole('button', { name: /Select code artifact Analysis Pipeline/ })).toHaveAttribute('aria-pressed', 'true');

    await userEvent.click(screen.getByRole('button', { name: /Select code artifact Model Training Utilities/ }));

    expect(screen.getByTestId('code-selected-download-region')).toHaveTextContent('Model Training Utilities');
    expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Model Training Utilities');
    expect(screen.getByRole('button', { name: /Select code artifact Model Training Utilities/ })).toHaveAttribute('aria-pressed', 'true');
  });

  it('keeps long code artifact metadata inside bounded rows and panels', async () => {
    const longName = 'Simulation pipeline with exceptionally long repository archive name for responsive layout validation';
    mockFetch(() => ({
      results: [
        {
          ...baseArtifact,
          id: 'long',
          name: longName,
          description: 'Long description '.repeat(24),
          tags: ['simulation', 'very-long-tag-name-for-layout', 'reproducibility'],
          sourcePathLabel: 'archives/' + 'nested-path-'.repeat(12) + 'source.zip',
          latestVersion: {
            ...baseArtifact.latestVersion,
            id: 'version-long',
            artifactId: 'long',
            filename: 'very-long-source-archive-name-for-layout-validation.zip',
            versionLabel: 'release-candidate-with-long-label',
          },
        },
      ],
    }));

    renderCodeRepository();

    await waitFor(() => expect(screen.getByTestId('code-results-list')).toHaveTextContent(longName));
    expect(within(screen.getByTestId('code-results-list')).getByText(longName)).toHaveClass('break-words');
    expect(screen.getByTestId('code-results-list')).toHaveClass('overflow-x-hidden');
    expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('very-long-source-archive-name-for-layout-validation.zip');
  });

  it('keeps upload available in empty, loading, and error states', async () => {
    let reject = false;
    mockFetch(() => {
      if (reject) {
        throw new Error('Code search failed');
      }
      return { results: [] };
    });

    renderCodeRepository();

    expect(await screen.findByText('No code artifacts')).toBeInTheDocument();
    expect(screen.getByText('Code archive upload')).toBeInTheDocument();

    reject = true;
    await userEvent.type(screen.getByPlaceholderText('Search name, description, tag'), 'error');

    expect((await screen.findAllByText('Code search failed')).length).toBeGreaterThan(0);
    expect(screen.getByText('Code archive upload')).toBeInTheDocument();
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
          actionCapabilities: {
            canView: true,
            canDownload: true,
            canRename: false,
            canDelete: false,
          },
        };
      }
      return { results: [] };
    });

    renderCodeRepository();
    expect(await screen.findByText('No code artifacts')).toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Choose archive' })).toBeInTheDocument();
    await userEvent.upload(
      screen.getByLabelText('Archive file'),
      new File(['zip'], 'uploaded.zip', { type: 'application/zip' }),
    );
    expect(screen.getByText('Selected archive: uploaded.zip')).toBeInTheDocument();
    expect(screen.getByText('3 bytes')).toBeInTheDocument();
    expect(screen.queryByText(/fakepath|Users|home/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upload archive' })).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Artifact name'), 'Uploaded Archive');
    expect(screen.getByRole('button', { name: 'Upload archive' })).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Artifact description'), 'Searchable implementation archive');
    expect(screen.getByRole('button', { name: 'Upload archive' })).toBeEnabled();
    await userEvent.click(screen.getByRole('button', { name: 'Upload archive' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
  });

  it('shows backend field validation instead of a generic bad request for archive uploads', async () => {
    mockFetch((url, init) => {
      if (init?.method === 'POST' && url.endsWith('/code-artifacts/')) {
        return {
          status: 400,
          json: {
            archive: ['Code uploads must be a compressed archive.'],
          },
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

    await waitFor(() => {
      expect(screen.getAllByText('archive: Code uploads must be a compressed archive.').length).toBeGreaterThan(0);
    });
    expect(screen.queryByText('Request failed with 400')).not.toBeInTheDocument();
  });

  it('supports clearing and reselecting archives with preflight validation', async () => {
    mockFetch(() => ({ results: [] }));

    renderCodeRepository();
    expect(await screen.findByText('No code artifacts')).toBeInTheDocument();
    expect(screen.getByText(/Allowed archives: .7z, .bz2, .gz, .tar, .tgz, .xz, .zip up to 100 MB/)).toBeInTheDocument();

    const archiveInput = screen.getByLabelText('Archive file');
    await userEvent.upload(archiveInput, new File(['bad'], 'notes.txt', { type: 'text/plain' }), { applyAccept: false });
    await waitFor(() => {
      expect(screen.getAllByText(/Choose a supported archive file/).length).toBeGreaterThan(0);
    });
    expect(screen.getByRole('button', { name: 'Upload archive' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Clear selected archive' }));
    expect(screen.queryByText('notes.txt')).not.toBeInTheDocument();

    await userEvent.upload(archiveInput, new File(['zip-again'], 'reselected.tgz', { type: 'application/gzip' }));
    expect(screen.getByText('Selected archive: reselected.tgz')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reselect archive' })).toBeInTheDocument();
  });

  it('blocks archives larger than the backend upload policy before submitting', async () => {
    mockFetch(() => ({ results: [] }));

    renderCodeRepository();
    expect(await screen.findByText('No code artifacts')).toBeInTheDocument();

    const oversizedArchive = new File(['zip'], 'too-large.zip', {
      type: 'application/zip',
    });
    Object.defineProperty(oversizedArchive, 'size', { value: codeUploadPolicy.maxSizeBytes + 1 });
    await userEvent.upload(screen.getByLabelText('Archive file'), oversizedArchive);

    await waitFor(() => {
      expect(screen.getAllByText('Choose an archive no larger than 100 MB.').length).toBeGreaterThan(0);
    });
    expect(screen.getByRole('button', { name: 'Upload archive' })).toBeDisabled();
  });

  it('shows maintainer rename and delete actions and syncs selected/list state', async () => {
    let artifacts = [
      {
        ...baseArtifact,
        actionCapabilities: {
          canView: true,
          canDownload: true,
          canRename: true,
          canDelete: true,
        },
      },
      {
        ...baseArtifact,
        id: '4',
        name: 'Delete Candidate',
        archiveFileId: '10',
        actionCapabilities: {
          canView: true,
          canDownload: true,
          canRename: true,
          canDelete: true,
        },
        latestVersion: { ...baseArtifact.latestVersion, id: 'version-4', artifactId: '4', filename: 'delete.zip' },
      },
    ];
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (init?.method === 'PATCH') {
        const renamed = { ...artifacts[0], name: 'Renamed Pipeline' };
        artifacts = [renamed, artifacts[1]];
        return { json: renamed };
      }
      if (init?.method === 'DELETE') {
        artifacts = artifacts.filter((artifact) => artifact.id !== '4');
        return { status: 204 };
      }
      return { results: artifacts };
    });

    renderCodeRepository();

    await waitFor(() => expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Analysis Pipeline'));
    await userEvent.click(screen.getByRole('button', { name: 'Rename code artifact' }));
    await userEvent.clear(screen.getByLabelText('New code artifact name'));
    await userEvent.type(screen.getByLabelText('New code artifact name'), 'Renamed Pipeline');
    await userEvent.click(screen.getByRole('button', { name: 'Save name' }));

    await waitFor(() => expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Renamed Pipeline'));
    expect(screen.getByTestId('code-results-list')).toHaveTextContent('Renamed Pipeline');
    expect(requests.some((request) => request.init?.method === 'PATCH')).toBe(true);

    await userEvent.click(screen.getByRole('button', { name: /Select code artifact Delete Candidate/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete code artifact' }));
    expect(screen.getByText(/Delete Delete Candidate/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));

    await waitFor(() => expect(screen.queryByText('Delete Candidate')).not.toBeInTheDocument());
    expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Renamed Pipeline');
    expect(requests.some((request) => request.init?.method === 'DELETE')).toBe(true);
  });

  it('hides rename and delete actions for unauthorized artifacts', async () => {
    mockFetch(() => ({ results: [baseArtifact] }));

    renderCodeRepository();

    await waitFor(() => expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Analysis Pipeline'));
    expect(screen.queryByRole('button', { name: 'Rename code artifact' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete code artifact' })).not.toBeInTheDocument();
  });

  it('uses shared code rename and delete endpoints for standalone maintainers', async () => {
    let artifacts = [
      {
        ...baseArtifact,
        actionCapabilities: {
          canView: true,
          canDownload: true,
          canRename: true,
          canDelete: true,
        },
      },
      {
        ...baseArtifact,
        id: '4',
        name: 'Shared Delete Candidate',
        actionCapabilities: {
          canView: true,
          canDownload: true,
          canRename: true,
          canDelete: true,
        },
        latestVersion: { ...baseArtifact.latestVersion, id: 'version-4', artifactId: '4', filename: 'delete.zip' },
      },
    ];
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.endsWith('/api/library/code/3/') && init?.method === 'PATCH') {
        const renamed = { ...artifacts[0], name: 'Renamed Shared Pipeline' };
        artifacts = [renamed, artifacts[1]];
        return { json: renamed };
      }
      if (url.endsWith('/api/library/code/4/') && init?.method === 'DELETE') {
        artifacts = artifacts.filter((artifact) => artifact.id !== '4');
        return { status: 204 };
      }
      return { count: artifacts.length, results: artifacts };
    });

    renderSharedCodeRepository();

    await waitFor(() => expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Analysis Pipeline'));
    await userEvent.click(screen.getByRole('button', { name: 'Rename code artifact' }));
    await userEvent.clear(screen.getByLabelText('New code artifact name'));
    await userEvent.type(screen.getByLabelText('New code artifact name'), 'Renamed Shared Pipeline');
    await userEvent.click(screen.getByRole('button', { name: 'Save name' }));

    await waitFor(() => expect(screen.getByTestId('code-selected-detail-region')).toHaveTextContent('Renamed Shared Pipeline'));
    expect(requests.some((request) => request.url.endsWith('/api/library/code/3/') && request.init?.method === 'PATCH')).toBe(true);

    await userEvent.click(screen.getByRole('button', { name: /Select code artifact Shared Delete Candidate/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete code artifact' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));

    await waitFor(() => expect(screen.queryByText('Shared Delete Candidate')).not.toBeInTheDocument());
    expect(requests.some((request) => request.url.endsWith('/api/library/code/4/') && request.init?.method === 'DELETE')).toBe(true);
  });
});
