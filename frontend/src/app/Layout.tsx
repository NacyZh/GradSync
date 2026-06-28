import type { PropsWithChildren } from 'react';

import { ProjectContextBanner } from '../features/projects/ProjectContextBanner';

export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <strong>GradSync</strong>
      </header>
      <ProjectContextBanner />
      <main>{children}</main>
    </div>
  );
}
