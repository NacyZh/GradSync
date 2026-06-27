import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ProjectSelector } from '../../src/features/projects/ProjectSelector';
import { TaskTree } from '../../src/features/tasks/TaskTree';

describe('project work UI', () => {
  it('shows selected project context', () => {
    render(<ProjectSelector projects={[{ id: 1, title: 'Project A' }]} selectedProjectId={1} onSelect={() => undefined} />);

    expect(screen.getByText('Project A')).toBeInTheDocument();
  });

  it('renders hierarchical tasks', () => {
    render(<TaskTree tasks={[{ id: 1, title: 'Parent', children: [{ id: 2, title: 'Child', children: [] }] }]} />);

    expect(screen.getByText('Parent')).toBeInTheDocument();
    expect(screen.getByText('Child')).toBeInTheDocument();
  });
});
