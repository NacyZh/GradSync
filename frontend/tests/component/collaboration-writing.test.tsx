import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { WritingProjectsPage } from '../../src/features/submissions/WritingProjectsPage';
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

function renderWritingProjects() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/projects/1/writing']}>
      <Routes>
        <Route path="/projects/:projectId/writing" element={<WritingProjectsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('collaboration writing UI', () => {
  it('shows writing project list, version history, feedback state, and annotated download', async () => {
    mockFetch((url) => {
      if (url.includes('/teacher-feedback/7/download')) {
        return { payload: { filename: 'annotated.docx', deliveryMode: 'direct_response' } };
      }
      return {
        payload: {
          results: [{
            id: '2',
            projectId: '1',
            studentId: '5',
            title: 'Thesis Chapter',
            writingType: 'thesis',
            status: 'active',
            versions: [{
              id: '6',
              writingProjectId: '2',
              versionNumber: 2,
              draftFileName: 'chapter.docx',
              fileKind: 'word',
              status: 'feedback_available',
              feedback: [{
                id: '7',
                writingVersionId: '6',
                reviewerId: '3',
                comments: 'Revise section two',
                status: 'notification_pending',
                annotatedFileName: 'annotated.docx',
                notificationStatus: 'pending',
              }],
            }],
          }],
        },
      };
    });

    renderWritingProjects();

    expect((await screen.findAllByText('Thesis Chapter')).length).toBeGreaterThan(1);
    expect(screen.getByText('Version 2')).toBeInTheDocument();
    expect(screen.getByText('Feedback available for version 2')).toBeInTheDocument();
    expect(screen.getByText('Revise section two')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Download annotated file/ }));
    expect(await screen.findByText(/annotated.docx/)).toBeInTheDocument();
  });

  it('creates a writing project, uploads a version, and submits teacher feedback', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (init?.method === 'POST' && url.endsWith('/writing-projects/')) {
        return {
          status: 201,
          payload: { id: '9', projectId: '1', studentId: '5', title: 'New Paper', writingType: 'paper', status: 'active', versions: [] },
        };
      }
      if (init?.method === 'POST' && url.includes('/writing-projects/2/versions')) {
        return {
          status: 201,
          payload: { id: '10', writingProjectId: '2', versionNumber: 2, status: 'submitted', draftFileName: 'revision.tex', feedback: [] },
        };
      }
      if (init?.method === 'POST' && url.includes('/writing-versions/6/feedback')) {
        return {
          status: 201,
          payload: { id: '11', writingVersionId: '6', reviewerId: '3', comments: 'Looks good', status: 'notification_pending', notificationStatus: 'pending' },
        };
      }
      return {
        payload: {
          results: [{
            id: '2',
            projectId: '1',
            studentId: '5',
            title: 'Existing Thesis',
            writingType: 'thesis',
            status: 'active',
            versions: [{ id: '6', writingProjectId: '2', versionNumber: 1, status: 'submitted', draftFileName: 'draft.docx', feedback: [] }],
          }],
        },
      };
    });

    renderWritingProjects();
    expect((await screen.findAllByText('Existing Thesis')).length).toBeGreaterThan(1);

    await userEvent.type(screen.getByLabelText('Writing project title'), 'New Paper');
    await userEvent.selectOptions(screen.getByLabelText('Writing type'), 'paper');
    await userEvent.click(screen.getByRole('button', { name: 'Create writing project' }));

    await userEvent.upload(screen.getByLabelText('Writing version file'), new File(['tex'], 'revision.tex', { type: 'text/x-tex' }));
    await userEvent.type(screen.getByLabelText('Version summary'), 'Revision');
    await userEvent.click(screen.getByRole('button', { name: 'Upload version' }));

    await userEvent.upload(screen.getByLabelText('Annotated file'), new File(['notes'], 'annotated.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }));
    await userEvent.type(screen.getByLabelText('Feedback comments'), 'Looks good');
    await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));

    await waitFor(() => expect(requests.filter((request) => request.method === 'POST').length).toBeGreaterThanOrEqual(3));
    expect(await screen.findByText('Version uploaded')).toBeInTheDocument();
    expect(await screen.findByText('Feedback saved and notification recorded')).toBeInTheDocument();
  });
});
