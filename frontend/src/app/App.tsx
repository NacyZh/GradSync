import { RouterProvider } from 'react-router-dom';

import { AppQueryProvider } from './queryClient';
import { AuthProvider } from '../features/auth/AuthProvider';
import { router } from '../routes';
import { AppFeedbackProvider } from '../shared/ui/AppFeedback';

export function App() {
  return (
    <AppQueryProvider>
      <AuthProvider>
        <AppFeedbackProvider>
          <RouterProvider router={router} />
        </AppFeedbackProvider>
      </AuthProvider>
    </AppQueryProvider>
  );
}
