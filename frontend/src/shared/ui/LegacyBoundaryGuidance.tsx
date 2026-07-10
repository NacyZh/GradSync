import { Link } from 'react-router-dom';

import { Button } from './primitives/button';

type LegacyBoundaryGuidanceProps = {
  mode: 'redirect' | 'guidance' | 'denied';
  targetPath?: string;
  message: string;
};

export function LegacyBoundaryGuidance({ mode, targetPath, message }: LegacyBoundaryGuidanceProps) {
  return (
    <section className="panel" aria-label="Moved workspace guidance">
      <h1>{mode === 'denied' ? 'Workspace access limited' : 'Workspace moved'}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
      {targetPath && mode !== 'denied' ? (
        <Button asChild className="mt-4">
          <Link to={targetPath}>Open workspace</Link>
        </Button>
      ) : null}
    </section>
  );
}
