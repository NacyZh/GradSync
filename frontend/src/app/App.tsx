import { RouterProvider } from 'react-router-dom';

import { AppQueryProvider } from './queryClient';
import { AuthProvider } from '../features/auth/AuthProvider';
import { router } from '../routes';

export function App() {
  return (
    <AppQueryProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </AppQueryProvider>
  );
}
