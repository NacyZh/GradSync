import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { RoleActivationPage } from '../../src/features/admin/RoleActivationPage';
import { ProfilePage } from '../../src/features/auth/ProfilePage';
import { RegisterPage } from '../../src/features/auth/RegisterPage';
import { AuthProvider } from '../../src/features/auth/AuthProvider';
import { StudentSelector } from '../../src/features/projects/StudentSelector';
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

describe('collaboration registration UI', () => {
  it('submits registration and verification forms', async () => {
    mockFetch((url) => {
      if (url.includes('/register/')) return { email: 's@example.com', status: 'pending_email_verification', requestedRole: 'student' };
      if (url.includes('/verify-email/')) return { id: 1, email: 's@example.com', name: 'Student', global_role: 'student', status: 'active' };
      return {};
    });

    renderWithClient(<MemoryRouter><RegisterPage /></MemoryRouter>);
    await userEvent.type(screen.getByLabelText('Email'), 's@example.com');
    await userEvent.type(screen.getByLabelText('Nickname'), 'Student');
    await userEvent.type(screen.getByLabelText('Password'), 'StrongPass1!');
    await userEvent.click(screen.getByRole('button', { name: 'Register' }));
    expect(await screen.findByText('Verification email sent')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Verification code'), '123456');
    await userEvent.click(screen.getByRole('button', { name: 'Verify email' }));
    expect(await screen.findByText('Email verified')).toBeInTheDocument();
  });

  it('updates profile nickname', async () => {
    mockFetch((url, init) => {
      if (url.includes('/api/accounts/me/') && init?.method === 'PATCH') {
        return { id: 1, email: 'a@example.com', name: 'New Nick', nickname: 'New Nick', global_role: 'admin', status: 'active' };
      }
      return { id: 1, email: 'a@example.com', name: 'Admin', nickname: 'Admin', global_role: 'admin', status: 'active' };
    });

    renderWithClient(
      <AuthProvider>
        <ProfilePage />
      </AuthProvider>,
    );
    const input = await screen.findByLabelText('Nickname');
    await userEvent.clear(input);
    await userEvent.type(input, 'New Nick');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('Profile updated')).toBeInTheDocument();
  });

  it('shows pending role activations and approves one', async () => {
    mockFetch((url, init) => {
      if (init?.method === 'PATCH') return { id: 1, status: 'approved', requestedRole: 'teacher', user: { id: 2, email: 't@example.com', name: 'Teacher', global_role: 'advisor', status: 'active' } };
      if (url.includes('/role-activations/')) return [{ id: 1, status: 'pending', requestedRole: 'teacher', activationSource: 'administrator_approval', createdAt: '2026-07-03T00:00:00Z', user: { id: 2, email: 't@example.com', name: 'Teacher', global_role: 'advisor', status: 'pending_role_activation' } }];
      return {};
    });

    renderWithClient(<RoleActivationPage />);
    expect(await screen.findByText('t@example.com')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
    expect(await screen.findByText('Activation updated')).toBeInTheDocument();
  });

  it('disambiguates student selector options by email and degree', async () => {
    mockFetch(() => [
      { id: 1, nickname: 'Alex', email: 'alex1@example.com', degreeType: 'masters', label: 'Alex <alex1@example.com>' },
      { id: 2, nickname: 'Alex', email: 'alex2@example.com', degreeType: 'doctoral', label: 'Alex <alex2@example.com>' },
    ]);
    const onSelect = vi.fn();

    renderWithClient(<StudentSelector onSelect={onSelect} />);
    await userEvent.type(screen.getByLabelText('Student nickname'), 'Alex');
    expect(await screen.findByText('alex1@example.com')).toBeInTheDocument();
    expect(screen.getByText('doctoral')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Student account'), '2');
    await userEvent.click(screen.getByRole('button', { name: 'Select student' }));
    await waitFor(() => expect(onSelect).toHaveBeenCalled());
  });
});
