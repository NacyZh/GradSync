import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { ProjectMaterialsPage } from '../../src/features/projects/ProjectMaterialsPage';
import { renderWithClient } from './test-utils';

function mockFetch(handler: (url: string, init?: RequestInit) => { payload: unknown; status?: number }) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const { payload, status = 200 } = handler(String(input), init);
    return new Response(JSON.stringify(payload), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

function renderProjectMaterials() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/projects/1/materials']}>
      <Routes>
        <Route path="/projects/:projectId/materials" element={<ProjectMaterialsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('project materials UI', () => {
  it('shows source project labels and capability-gated visibility controls for owners', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (init?.method === 'PATCH') {
        return {
          payload: {
            id: '44',
            materialType: 'document',
            backingRecordId: '9',
            displayName: 'Protocol',
            sourceProject: { id: '1', title: 'Boundary Project' },
            visibility: 'group-wide',
            classificationState: 'active',
            actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: true },
          },
        };
      }
      if (init?.method === 'POST') {
        return {
          status: 201,
          payload: {
            id: '45',
            materialType: 'document',
            backingRecordId: '10',
            displayName: 'New Protocol',
            sourceProject: { id: '1', title: 'Boundary Project' },
            visibility: 'project-only',
            classificationState: 'active',
            actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: true },
          },
        };
      }
      return {
        payload: {
          count: 1,
          results: [{
            id: '44',
            materialType: 'document',
            backingRecordId: '9',
            displayName: 'Protocol',
            sourceProject: { id: '1', title: 'Boundary Project' },
            visibility: 'project-only',
            classificationState: 'active',
            actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: true },
          }],
        },
      };
    });

    renderProjectMaterials();

    expect(await screen.findByText('Protocol')).toBeInTheDocument();
    expect(screen.getAllByText('Project-only').length).toBeGreaterThan(0);
    expect(screen.getByText('Source: Boundary Project')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Set group-wide' }));
    await waitFor(() => expect(requests.some((request) => request.method === 'PATCH')).toBe(true));
  });

  it('hides visibility controls for ordinary members', async () => {
    mockFetch(() => ({
      payload: {
        count: 1,
        results: [{
          id: '46',
          materialType: 'code',
          backingRecordId: '12',
          displayName: 'Analysis Code',
          sourceProject: { id: '1', title: 'Boundary Project' },
          visibility: 'project-only',
          classificationState: 'active',
          actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: false },
        }],
      },
    }));

    renderProjectMaterials();

    expect(await screen.findByText('Analysis Code')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Set group-wide' })).not.toBeInTheDocument();
  });

  it('uses the shared file picker pattern and clears a selected material', async () => {
    mockFetch(() => ({ payload: { count: 0, results: [] } }));
    renderProjectMaterials();

    expect(await screen.findByRole('button', { name: 'Choose material file' })).toBeInTheDocument();
    await userEvent.upload(screen.getByLabelText('Material file'), new File(['notes'], 'notes.md', { type: 'text/markdown' }));
    expect(screen.getByText('Selected file: notes.md')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Clear material file' }));
    expect(screen.queryByText('Selected file: notes.md')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upload material' })).toBeDisabled();
  });
});
