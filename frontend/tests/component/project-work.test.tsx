import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { HomePage } from '../../src/app/HomePage';
import { ProjectSelector } from '../../src/features/projects/ProjectSelector';
import { TaskTree } from '../../src/features/tasks/TaskTree';
import { renderWithClient } from './test-utils';

describe('project work UI', () => {
  it('renders a useful application home screen', () => {
    renderWithClient(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'GradSync' })).toBeInTheDocument();
    expect(screen.getByText(/Research group operations/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'New project' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Resources' })).toBeInTheDocument();
  });

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
