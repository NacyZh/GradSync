import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { vi } from 'vitest';

import type { CurrentUser } from '../../src/features/auth/AuthProvider';
import { AppFeedbackProvider } from '../../src/shared/ui/AppFeedback';

type RenderWithClientOptions = {
  includeFeedbackProvider?: boolean;
};

export function renderWithClient(ui: ReactElement, options: RenderWithClientOptions = {}) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const content = options.includeFeedbackProvider === false ? ui : <AppFeedbackProvider>{ui}</AppFeedbackProvider>;

  return render(<QueryClientProvider client={client}>{content}</QueryClientProvider>);
}

export function mockCurrentUserFetch(user: CurrentUser | null) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url) => {
      if (!String(url).includes('/api/accounts/me/')) {
        return Promise.resolve(
          new Response(JSON.stringify({ results: [] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (user) {
        return Promise.resolve(
          new Response(JSON.stringify(user), {
            status: 200,
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
    }),
  );
}
