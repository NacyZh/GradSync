import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';

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
