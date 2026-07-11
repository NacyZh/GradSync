import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { WritingProjectsPage } from '../../src/features/submissions/WritingProjectsPage';
import { renderWithClient } from './test-utils';

function mockFetch(handler: (url: string, init?: RequestInit) => { payload: unknown; status?: number } | Response) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const result = handler(String(input), init);
    if (result instanceof Response) {
      return result;
    }
    const { payload, status = 200 } = result;
    return new Response(JSON.stringify(payload), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

function renderWritingProjects(initialEntry = '/writing') {
  return renderWithClient(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/writing" element={<WritingProjectsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('collaboration writing UI', () => {
  it('shows writing project list, version history, feedback state, and annotated download', async () => {
    const createObjectURL = vi.fn(() => 'blob:feedback-download');
    const revokeObjectURL = vi.fn();
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    mockFetch((url) => {
      if (url.includes('/writing-versions/6/download')) {
        return new Response(new Blob(['draft']), {
          status: 200,
          headers: { 'Content-Disposition': 'attachment; filename="chapter.docx"' },
        });
      }
      if (url.includes('/teacher-feedback/7/download')) {
        return new Response(new Blob(['feedback']), {
          status: 200,
          headers: { 'Content-Disposition': 'attachment; filename="annotated.docx"' },
        });
      }
      return {
        payload: {
          results: [{
            id: '2',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'Thesis Chapter',
            writingType: 'thesis',
            participantRole: 'student_author',
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

    await userEvent.click(screen.getByRole('button', { name: /Download draft file/ }));
    expect(await screen.findByText('Download started: chapter.docx')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Download annotated file/ }));
    expect(await screen.findByText(/annotated.docx/)).toBeInTheDocument();
    expect(createObjectURL).toHaveBeenCalled();
    expect(anchorClick).toHaveBeenCalled();
  });

  it('creates a writing project and uploads a version as the student author', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (init?.method === 'POST' && url.endsWith('/writing-projects/')) {
        return {
          status: 201,
          payload: { id: '9', projectId: '1', legacyProjectId: '1', studentId: '5', title: 'New Paper', writingType: 'paper', participantRole: 'student_author', status: 'active', versions: [] },
        };
      }
      if (init?.method === 'POST' && url.includes('/writing-projects/2/versions')) {
        return {
          status: 201,
          payload: { id: '10', writingProjectId: '2', versionNumber: 2, status: 'submitted', draftFileName: 'revision.tex', feedback: [] },
        };
      }
      return {
        payload: {
          results: [{
            id: '2',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'Existing Thesis',
            writingType: 'thesis',
            participantRole: 'student_author',
            status: 'active',
            versions: [{ id: '6', writingProjectId: '2', versionNumber: 1, status: 'submitted', draftFileName: 'draft.docx', feedback: [] }],
          }],
        },
      };
    });

    renderWritingProjects();
    expect((await screen.findAllByText('Existing Thesis')).length).toBeGreaterThan(1);
    expect(screen.getByRole('button', { name: 'Choose version' })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Writing project title'), 'New Paper');
    await userEvent.selectOptions(screen.getByLabelText('Writing type'), 'paper');
    await userEvent.click(screen.getByRole('button', { name: 'Create writing project' }));

    await userEvent.upload(screen.getByLabelText('Writing version file'), new File(['tex'], 'revision.tex', { type: 'text/x-tex' }));
    expect(screen.getByText('Selected file: revision.tex')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clear writing version file' })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Version summary'), 'Revision');
    await userEvent.click(screen.getByRole('button', { name: 'Upload version' }));

    await waitFor(() => expect(requests.filter((request) => request.method === 'POST').length).toBeGreaterThanOrEqual(2));
    expect(await screen.findByText('Version uploaded')).toBeInTheDocument();
    expect(screen.queryByLabelText('Annotated file')).not.toBeInTheDocument();
  });

  it('submits teacher feedback as an assigned reviewer with an English file picker', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
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
            legacyProjectId: '1',
            studentId: '5',
            title: 'Reviewable Thesis',
            writingType: 'thesis',
            participantRole: 'assigned_reviewer',
            status: 'active',
            versions: [{ id: '6', writingProjectId: '2', versionNumber: 1, status: 'under_review', draftFileName: 'draft.docx', feedback: [] }],
          }],
        },
      };
    });

    renderWritingProjects();
    expect(await screen.findByRole('button', { name: 'Choose feedback file' })).toBeInTheDocument();

    await userEvent.upload(screen.getByLabelText('Annotated file'), new File(['notes'], 'annotated.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }));
    expect(screen.getByText('Selected file: annotated.docx')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Feedback comments'), 'Looks good');
    await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));

    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));
    expect(await screen.findByText('Feedback saved and notification recorded')).toBeInTheDocument();
  });

  it('shows reviewer state without student upload controls', async () => {
    mockFetch(() => ({
      payload: {
        results: [{
          id: '12',
          projectId: '1',
          legacyProjectId: '1',
          studentId: '5',
          title: 'Reviewable Manuscript',
          writingType: 'manuscript',
          participantRole: 'assigned_reviewer',
          status: 'active',
          versions: [{ id: '13', writingProjectId: '12', versionNumber: 1, status: 'submitted', draftFileName: 'draft.docx', feedback: [] }],
        }],
      },
    }));

    renderWritingProjects();

    expect(await screen.findByText('assigned reviewer')).toBeInTheDocument();
    expect(screen.queryByLabelText('Writing version file')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Rename' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
    expect(screen.getByText('Version uploads are available to the student author.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Choose feedback file' })).toBeInTheDocument();
  });

  it('renames and deletes a writing project as the student author', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockFetch((url, init) => {
      if (init?.method === 'PATCH' && url.includes('/writing-projects/2/')) {
        return {
          payload: {
            id: '2',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'Renamed Thesis',
            writingType: 'thesis',
            participantRole: 'student_author',
            status: 'active',
            versions: [],
          },
        };
      }
      if (init?.method === 'DELETE' && url.includes('/writing-projects/2/')) {
        return new Response(null, { status: 204 });
      }
      return {
        payload: {
          results: [{
            id: '2',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'Original Thesis',
            writingType: 'thesis',
            participantRole: 'student_author',
            status: 'active',
            versions: [],
          }],
        },
      };
    });

    renderWritingProjects();
    expect(await screen.findByRole('heading', { name: 'Original Thesis' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Rename' }));
    await userEvent.clear(screen.getByLabelText('Rename writing project'));
    await userEvent.type(screen.getByLabelText('Rename writing project'), 'Renamed Thesis');
    await userEvent.click(screen.getByRole('button', { name: 'Save rename' }));

    expect(await screen.findByRole('heading', { name: 'Renamed Thesis' })).toBeInTheDocument();
    expect(screen.getByText('Writing project renamed')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(confirm).toHaveBeenCalled();
    expect(await screen.findByText('Writing project deleted')).toBeInTheDocument();
  });

  it('selects a writing project from notification deep links', async () => {
    mockFetch(() => ({
      payload: {
        results: [
          {
            id: '11',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: '1',
            writingType: 'thesis',
            participantRole: 'student_author',
            status: 'active',
            versions: [],
          },
          {
            id: '12',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'Linked Manuscript',
            writingType: 'manuscript',
            participantRole: 'student_author',
            status: 'active',
            versions: [{ id: '13', writingProjectId: '12', versionNumber: 1, status: 'feedback_available', draftFileName: 'linked.docx', feedback: [] }],
          },
        ],
      },
    }));

    renderWritingProjects('/writing?writingProjectId=12');

    expect(await screen.findByText('Writing project 1')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Linked Manuscript' })).toBeInTheDocument();
    expect(screen.getByText('Version 1')).toBeInTheDocument();
  });

  it('shows backend feedback download errors', async () => {
    mockFetch((url) => {
      if (url.includes('/teacher-feedback/7/download')) {
        return new Response(JSON.stringify({ message: 'File is no longer available' }), {
          status: 410,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return {
        payload: {
          results: [{
            id: '2',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'Thesis Chapter',
            writingType: 'thesis',
            participantRole: 'student_author',
            status: 'active',
            versions: [{
              id: '6',
              writingProjectId: '2',
              versionNumber: 1,
              draftFileName: 'chapter.docx',
              status: 'feedback_available',
              feedback: [{
                id: '7',
                writingVersionId: '6',
                reviewerId: '3',
                comments: 'Revise section two',
                status: 'notification_pending',
                annotatedFileName: 'annotated.docx',
              }],
            }],
          }],
        },
      };
    });

    renderWritingProjects();

    await userEvent.click(await screen.findByRole('button', { name: /Download annotated file/ }));

    expect(await screen.findByText('File is no longer available')).toBeInTheDocument();
  });

  it('renders an empty standalone writing state without hidden private metadata', async () => {
    mockFetch(() => ({ payload: { results: [] } }));

    renderWritingProjects();

    expect(await screen.findByText('No writing projects')).toBeInTheDocument();
    expect(screen.queryByText('Private Boundary Draft')).not.toBeInTheDocument();
  });
});
