import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../src/features/auth/AuthProvider';
import { LoginPage } from '../../src/features/auth/LoginPage';
import { renderWithClient } from './test-utils';

function renderLogin() {
  return renderWithClient(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe('login page', () => {
  beforeEach(() => {
    // Return 401 so AuthProvider resolves user=null.
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ message: 'Authentication required' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          }),
        ),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the sign-in form with accessible controls after auth check', async () => {
    renderLogin();

    await screen.findByRole('heading', { name: 'GradSync' });

    expect(screen.getByText(/Sign in to your research group account/)).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toHaveAttribute('type', 'email');
    expect(screen.getByLabelText('Email')).toHaveAttribute('autocomplete', 'email');
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'current-password');
    expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('keeps authentication fields aligned and toggles password visibility accessibly', async () => {
    renderLogin();
    await screen.findByRole('heading', { name: 'GradSync' });

    const email = screen.getByLabelText('Email');
    const password = screen.getByLabelText('Password');
    expect(email).toHaveClass('login-input');
    expect(password).toHaveClass('login-input');
    expect(email.closest('.login-field')).toBeInTheDocument();
    expect(password.closest('.login-field')).toBeInTheDocument();

    const toggle = screen.getByRole('button', { name: 'Show password' });
    expect(password).toHaveAttribute('type', 'password');
    await userEvent.click(toggle);
    expect(password).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: 'Hide password' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('keeps submit disabled when only one field is filled', async () => {
    renderLogin();
    await screen.findByRole('heading', { name: 'GradSync' });

    const submitButton = screen.getByRole('button', { name: 'Sign in' });
    expect(submitButton).toBeDisabled();

    await userEvent.type(screen.getByLabelText('Email'), 'test@example.edu');
    expect(submitButton).toBeDisabled();

    await userEvent.clear(screen.getByLabelText('Email'));
    await userEvent.type(screen.getByLabelText('Password'), 'password123');
    expect(submitButton).toBeDisabled();
  });

  it('enables submit when both email and password are filled', async () => {
    renderLogin();
    await screen.findByRole('heading', { name: 'GradSync' });

    const submitButton = screen.getByRole('button', { name: 'Sign in' });
    await userEvent.type(screen.getByLabelText('Email'), 'test@example.edu');
    await userEvent.type(screen.getByLabelText('Password'), 'password123');

    expect(submitButton).not.toBeDisabled();
  });

  it('submits credentials to the login endpoint and shows error on failure', async () => {
    renderLogin();
    await screen.findByRole('heading', { name: 'GradSync' });

    await userEvent.type(screen.getByLabelText('Email'), 'wrong@example.edu');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password');

    // Override fetch for the login call to return 400.
    const fetchSpy = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        return Promise.resolve(
          new Response(JSON.stringify({ message: 'Invalid email or password' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ message: 'Authentication required' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });
    vi.stubGlobal('fetch', fetchSpy);

    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    // After the mutation fails, the error message should appear.
    await screen.findByRole('alert');
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid email or password');

    // Verify fetch was called with the login endpoint and correct payload.
    const loginCall = fetchSpy.mock.calls.find(
      ([url, init]: [string, RequestInit?]) =>
        url.includes('/api/accounts/login/') && init?.method === 'POST',
    );
    expect(loginCall).toBeDefined();
    const body = JSON.parse((loginCall![1] as RequestInit).body as string);
    expect(body).toEqual({ email: 'wrong@example.edu', password: 'wrong-password' });
  });
});
