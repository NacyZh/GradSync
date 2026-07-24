import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProjectCollaboratorsPanel } from '../../src/features/projects/ProjectCollaboratorsPanel';
import { renderWithClient } from './test-utils';

describe('project governance', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('searches eligible teachers only after opening and typing', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          results: [
            {
              id: 7,
              name: 'Teacher Seven',
              nickname: 'T7',
              email: 'teacher7@example.edu',
              label: 'T7',
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    renderWithClient(
      <ProjectCollaboratorsPanel
        projectId={1}
        members={[]}
        canManage
      />,
    );

    expect(fetchMock).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('combobox', { name: 'Teacher account' }));
    await userEvent.type(screen.getByLabelText('Search eligible teachers'), 'te');
    expect(await screen.findByText('teacher7@example.edu')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('omits collaborator controls for read-only roles', () => {
    renderWithClient(
      <ProjectCollaboratorsPanel
        projectId={1}
        members={[
          {
            id: 2,
            role: 'observer',
            status: 'active',
            name: 'Observer',
          },
        ]}
        canManage={false}
      />,
    );

    expect(screen.getByText('Observer')).toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });
});
