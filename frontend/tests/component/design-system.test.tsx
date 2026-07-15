import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { Button } from '../../src/shared/ui/primitives/button';
import { Input } from '../../src/shared/ui/primitives/input';
import { Label } from '../../src/shared/ui/primitives/label';
import { Tooltip, TooltipContent, TooltipTrigger } from '../../src/shared/ui/primitives/tooltip';
import { ProjectContextBar } from '../../src/shared/ui/ProjectContextBar';
import { DataState } from '../../src/shared/ui/DataState';
import { FeedbackProvider, useFeedback } from '../../src/shared/ui/FeedbackProvider';
import { FormField } from '../../src/shared/ui/FormField';
import { StatusBadge } from '../../src/shared/ui/StatusBadge';
import { renderWithClient } from './test-utils';

function FeedbackHarness() {
  const { notify, confirm, theme, toggleTheme } = useFeedback();
  return (
    <div>
      <button type="button" onClick={() => notify('Project saved', 'success')}>Toast</button>
      <button
        type="button"
        onClick={() => {
          confirm({ title: 'Archive project', message: 'Archive this project?', actionLabel: 'Archive' });
        }}
      >
        Confirm
      </button>
      <button type="button" onClick={toggleTheme}>Theme {theme}</button>
    </div>
  );
}

describe('production design system', () => {
  it('loads reusable primitives from the shared UI primitive boundary', () => {
    expect(Button).toBeDefined();
    expect(Input).toBeDefined();
    expect(Label).toBeDefined();
    expect(Tooltip).toBeDefined();
  });

  it('renders shadcn-style buttons, labels, fields, badges, and project workflow navigation', () => {
    renderWithClient(
      <div>
        <Label htmlFor="query">Query</Label>
        <Input id="query" placeholder="Search records" />
        <Button>Save</Button>
        <StatusBadge status="needs_revision" />
        <FormField id="title" label="Title" error="Title is required" />
        <MemoryRouter>
          <ProjectContextBar projectId={12} userRole="advisor" />
        </MemoryRouter>
      </div>,
    );

    expect(screen.getByLabelText('Query')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
    expect(screen.getByText('needs revision')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Title is required');
    expect(screen.queryByLabelText('Selected project context')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Project workflow' })).toHaveTextContent('Materials');
    expect(screen.getByRole('link', { name: 'Reviews' })).toHaveAttribute('href', '/projects/12/reviews');
    expect(screen.queryByRole('link', { name: 'Drafts' })).not.toBeInTheDocument();
  });

  it('shows student project workflow entries without advisor review queue', () => {
    renderWithClient(
      <MemoryRouter>
        <ProjectContextBar projectId={12} userRole="student" />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Materials' })).toHaveAttribute('href', '/projects/12/materials');
    expect(screen.getByRole('link', { name: 'Drafts' })).toHaveAttribute('href', '/projects/12/drafts');
    expect(screen.getByRole('link', { name: 'Reports' })).toHaveAttribute('href', '/projects/12/reports');
    expect(screen.queryByRole('link', { name: 'Reviews' })).not.toBeInTheDocument();
  });

  it('announces loading, empty, success, warning, and error data states', () => {
    renderWithClient(
      <div>
        <DataState state="loading" message="Loading tasks" />
        <DataState state="empty" message="No records" />
        <DataState state="success" message="Saved" />
        <DataState state="warning" message="Archived project" />
        <DataState state="error" message="Request failed" />
      </div>,
    );

    expect(screen.getAllByRole('status').length).toBeGreaterThanOrEqual(4);
    expect(screen.getByRole('alert')).toHaveTextContent('Request failed');
  });

  it('provides toast feedback, confirmation dialog focus behavior, tooltips, and theme switching', async () => {
    const user = userEvent.setup();

    renderWithClient(
      <FeedbackProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button">Icon action</button>
          </TooltipTrigger>
          <TooltipContent>Action tooltip</TooltipContent>
        </Tooltip>
        <FeedbackHarness />
      </FeedbackProvider>,
      { includeFeedbackProvider: false },
    );

    await user.click(screen.getByRole('button', { name: 'Toast' }));
    expect(await screen.findByText('Project saved')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Theme/ }));
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe('dark'));

    await user.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(screen.getByRole('dialog', { name: 'Archive project' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Archive' })).toBeInTheDocument();
  });
});
