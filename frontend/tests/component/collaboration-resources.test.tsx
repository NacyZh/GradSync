import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../src/features/auth/AuthProvider';
import { ResourceListPage } from '../../src/features/resources/ResourceListPage';
import { renderWithClient } from './test-utils';

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const payload = handler(String(input), init);
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

function renderResources() {
  return renderWithClient(
    <AuthProvider>
      <MemoryRouter initialEntries={['/projects/1/resources']}>
        <Routes>
          <Route path="/projects/:projectId/resources" element={<ResourceListPage />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe('collaboration resources UI', () => {
  it('shows manager controls, use submission form, and decision queue for teachers', async () => {
    const requests: RequestInit[] = [];
    mockFetch((url, init) => {
      requests.push(init ?? {});
      if (url.includes('/api/accounts/me/')) {
        return { id: 10, email: 'teacher@example.edu', name: 'Teacher', global_role: 'advisor', status: 'active' };
      }
      if (url.includes('/api/resource-use-submissions/') && init?.method === 'PATCH') {
        return {
          id: 3,
          resourceId: 2,
          studentId: 11,
          submissionType: 'request',
          details: 'Need access',
          status: 'confirmed',
          decisionNote: 'Approved',
        };
      }
      if (url.includes('/api/resources/2/use-submissions/') && init?.method === 'POST') {
        return {
          id: 4,
          resourceId: 2,
          studentId: 10,
          submissionType: 'use_record',
          details: 'Recorded session',
          status: 'pending',
        };
      }
      if (url.endsWith('/api/resources/') && init?.method === 'POST') {
        return {
          id: 5,
          name: 'New microscope',
          resourceType: 'Microscope',
          description: 'Created from UI',
          status: 'active',
          useInstructions: 'Ask first',
          useSubmissions: [],
        };
      }
      if (url.endsWith('/api/resources/')) {
        return {
          results: [{
            id: 2,
            name: 'Confocal microscope',
            resourceType: 'Microscope',
            description: 'Imaging station',
            status: 'active',
            useInstructions: 'Request time before use.',
            useSubmissions: [{
              id: 3,
              resourceId: 2,
              studentId: 11,
              studentName: 'Student One',
              submissionType: 'request',
              details: 'Need access',
              status: 'pending',
            }],
          }],
        };
      }
      if (url.includes('/resource-items/availability/')) return [];
      if (url.includes('/resource-types')) return { results: [] };
      if (url.includes('/resource-items')) return { results: [] };
      if (url.includes('/bookings')) return { results: [] };
      if (url.includes('/notifications')) return { results: [] };
      return { results: [] };
    });

    renderResources();

    expect((await screen.findAllByText('Confocal microscope')).length).toBeGreaterThan(0);
    expect(screen.getByRole('form', { name: 'Manage resource inventory' })).toBeInTheDocument();
    expect(screen.getByRole('form', { name: 'Submit resource use' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Resource use submissions' })).toHaveTextContent('Need access');

    await userEvent.type(screen.getByLabelText('Resource name'), 'New microscope');
    await userEvent.type(screen.getByLabelText('Resource type'), 'Microscope');
    await userEvent.click(screen.getByRole('button', { name: 'Create resource' }));
    await waitFor(() => expect(requests.some((request) => request.method === 'POST')).toBe(true));

    await userEvent.click(screen.getByRole('button', { name: 'Confirm submission' }));
    expect(await screen.findByText('Submission confirmed')).toBeInTheDocument();
  });

  it('keeps student inventory management hidden while allowing use submissions', async () => {
    mockFetch((url, init) => {
      if (url.includes('/api/accounts/me/')) {
        return { id: 11, email: 'student@example.edu', name: 'Student', global_role: 'student', status: 'active' };
      }
      if (url.includes('/api/resources/2/use-submissions/') && init?.method === 'POST') {
        return { id: 7, resourceId: 2, studentId: 11, submissionType: 'request', details: 'Need access', status: 'pending' };
      }
      if (url.endsWith('/api/resources/')) {
        return {
          results: [{ id: 2, name: 'Confocal microscope', resourceType: 'Microscope', status: 'active', useSubmissions: [] }],
        };
      }
      if (url.includes('/resource-items/availability/')) return [];
      if (url.includes('/resource-types')) return { results: [] };
      if (url.includes('/resource-items')) return { results: [] };
      if (url.includes('/bookings')) return { results: [] };
      if (url.includes('/notifications')) return { results: [] };
      return { results: [] };
    });

    renderResources();

    expect((await screen.findAllByText('Confocal microscope')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('form', { name: 'Manage resource inventory' })).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: 'Submit resource use' })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Use details'), 'Need access');
    await userEvent.click(screen.getByRole('button', { name: 'Submit use request' }));
    expect(await screen.findByText('Use submission pending')).toBeInTheDocument();
  });
});
