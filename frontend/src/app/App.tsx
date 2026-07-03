import { RouterProvider } from 'react-router-dom';

import { AppQueryProvider } from './queryClient';
import { AuthProvider } from '../features/auth/AuthProvider';
import { AppLocaleProvider } from '../features/i18n/AppLocaleProvider';
import { router } from '../routes';
import { AppFeedbackProvider } from '../shared/ui/AppFeedback';

export function App() {
  return (
    <AppQueryProvider>
      <AuthProvider>
        <AppLocaleProvider>
          <AppFeedbackProvider>
            <RouterProvider router={router} />
          </AppFeedbackProvider>
        </AppLocaleProvider>
      </AuthProvider>
    </AppQueryProvider>
  );
}
