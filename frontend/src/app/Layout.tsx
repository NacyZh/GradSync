import type { PropsWithChildren } from 'react';

import { ProjectContextBanner } from '../features/projects/ProjectContextBanner';

export function Layout({ children }: PropsWithChildren) {
  return (
    <div>
      <header>
        <strong>GradSync</strong>
      </header>
      <ProjectContextBanner />
      <main>{children}</main>
    </div>
  );
}
