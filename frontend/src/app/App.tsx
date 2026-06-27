import { RouterProvider } from 'react-router-dom';

import { AppQueryProvider } from './queryClient';
import { AuthProvider } from '../features/auth/AuthProvider';
import { Layout } from './Layout';
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

export function HomePage() {
  return (
    <Layout>
      <section>
        <h1>GradSync</h1>
      </section>
    </Layout>
  );
}
