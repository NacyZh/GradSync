import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';

import { AppFeedbackProvider } from '../../src/shared/ui/AppFeedback';

export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <AppFeedbackProvider>{ui}</AppFeedbackProvider>
    </QueryClientProvider>,
  );
}
