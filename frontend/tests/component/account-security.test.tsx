import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ForgotPasswordPage } from '../../src/features/auth/ForgotPasswordPage';
import { renderWithClient } from './test-utils';

describe('account security', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('uses one generic recovery acknowledgement', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              message: 'If the account is eligible, recovery instructions will be sent.',
            }),
            { status: 202, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );
    renderWithClient(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText('Email'), 'person@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send recovery instructions' }));
    expect(
      await screen.findByText('If the account is eligible, recovery instructions will be sent.'),
    ).toBeInTheDocument();
  });
});

