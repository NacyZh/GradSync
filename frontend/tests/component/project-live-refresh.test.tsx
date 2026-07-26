import { readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

describe('project execution live refresh boundaries', () => {
  it('registers every execution query through the public projects surface', () => {
    const projectIndex = readFileSync(
      path.join(process.cwd(), 'src/features/projects/index.ts'),
      'utf8',
    );
    const liveRefresh = readFileSync(
      path.join(process.cwd(), 'src/features/projects/useProjectLiveRefresh.ts'),
      'utf8',
    );
    for (const key of [
      'project-execution',
      'project-milestones',
      'project-deliverables',
      'project-report-templates',
      'project-report-analytics',
      'project-decisions',
      'project-risks',
      'project-notification-policy',
    ]) {
      expect(projectIndex).toContain(key);
    }
    expect(liveRefresh).toContain("from './index'");
    expect(liveRefresh).toContain('projectExecutionQueryKeys(projectId)');
  });
});
