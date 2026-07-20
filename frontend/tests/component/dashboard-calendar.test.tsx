import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { CalendarAgenda } from '../../src/features/schedules/CalendarAgenda';
import { CalendarGrid } from '../../src/features/schedules/CalendarGrid';
import { CalendarToolbar } from '../../src/features/schedules/CalendarToolbar';
import { ScheduleDetailPanel } from '../../src/features/schedules/ScheduleDetailPanel';
import type { CalendarOccurrence } from '../../src/features/schedules/api';
import { renderWithClient } from './test-utils';

const task: CalendarOccurrence = {
  occurrenceId: 'task:1:2026-07-20T08:00:00Z',
  sourceType: 'task',
  sourceId: '1',
  scope: 'system',
  category: 'task',
  title: 'Analyze samples',
  startsAt: '2026-07-20T08:00:00Z',
  endsAt: '2026-07-20T09:00:00Z',
  allDay: false,
  timezone: 'UTC',
  status: 'active',
  actionPath: '/projects/1?task=1',
  capabilities: {
    canView: true,
    canEdit: false,
    canDelete: false,
    canPublish: false,
    canCancel: false,
    canViewDeliveryStatus: false,
    isReadOnly: true,
  },
};

describe('dashboard calendar', () => {
  it('switches calendar views and exposes source filters', async () => {
    const onViewChange = vi.fn();
    renderWithClient(
      <CalendarToolbar
        anchor={new Date('2026-07-20T00:00:00Z')}
        view="month"
        sources={['task', 'report']}
        onAnchorChange={() => undefined}
        onViewChange={onViewChange}
        onSourcesChange={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Week' }));
    expect(onViewChange).toHaveBeenCalledWith('week');
    await userEvent.click(screen.getByRole('button', { name: /Filter calendar sources/ }));
    expect(screen.getByRole('group', { name: 'Calendar sources' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Reports' })).toBeChecked();
  });

  it('renders keyboard-selectable grid and agenda occurrences', async () => {
    const onSelect = vi.fn();
    renderWithClient(
      <>
        <CalendarGrid
          anchor={new Date('2026-07-20T00:00:00Z')}
          view="week"
          occurrences={[task]}
          selectedId={null}
          onSelect={onSelect}
        />
        <CalendarAgenda occurrences={[task]} selectedId={null} onSelect={onSelect} />
      </>,
    );

    await userEvent.click(screen.getAllByRole('button', { name: /Analyze samples/ })[0]);
    expect(onSelect).toHaveBeenCalledWith(task);
    expect(screen.getAllByText('Task', { selector: 'span' }).length).toBeGreaterThan(0);
  });

  it('shows read-only source details without unsupported actions', () => {
    renderWithClient(
      <MemoryRouter>
        <ScheduleDetailPanel occurrence={task} />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Analyze samples' })).toBeInTheDocument();
    expect(screen.getByText('Read-only project data')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open source' })).toHaveAttribute('href', task.actionPath);
    expect(screen.queryByRole('button', { name: /Edit/ })).not.toBeInTheDocument();
  });

  it('uses the empty detail region for an upcoming schedule list', () => {
    renderWithClient(
      <MemoryRouter>
        <ScheduleDetailPanel occurrence={null} upcoming={[task]} onSelect={() => undefined} />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Upcoming' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Analyze samples/ })).toBeInTheDocument();
  });

  it('renders schedule text as text instead of executable markup', () => {
    const unsafe = {
      ...task,
      title: '<script>window.__calendarXss = true</script>',
      description: '<img src=x onerror="window.__calendarXss = true">',
    };
    renderWithClient(
      <MemoryRouter>
        <ScheduleDetailPanel occurrence={unsafe} />
      </MemoryRouter>,
    );
    expect(screen.getByText(unsafe.title)).toBeInTheDocument();
    expect(screen.getByText(unsafe.description)).toBeInTheDocument();
    expect(document.querySelector('.calendar-detail script')).toBeNull();
    expect(document.querySelector('.calendar-detail img')).toBeNull();
  });
});
