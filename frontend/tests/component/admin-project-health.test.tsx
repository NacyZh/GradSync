import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { ProjectHealthPage } from '../../src/features/admin/ProjectHealthPage';
import { renderWithClient } from './test-utils';

describe('administrator project health operations', () => {
  it('renders cross-project metrics, risk ranking, trend, and intervention queues', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      generatedAt: '2026-07-29T08:00:00Z',
      windowDays: 30,
      longBlockedDays: 7,
      summary: {
        activeProjects: 2,
        overdueProjects: 1,
        overdueProjectRate: 50,
        longBlockedTasks: 1,
        missingReports: 2,
        governanceHolds: 1,
        resourceConflicts: 3,
        notificationFailures: 2,
        notificationFailureRate: 25,
      },
      projects: [{
        projectId: 7,
        title: 'Delayed imaging study',
        advisorName: 'Advisor One',
        endsOn: '2026-07-20',
        overdue: true,
        openTaskCount: 6,
        overdueTaskCount: 3,
        longBlockedTaskCount: 1,
        missingReportCount: 2,
        governanceState: 'hold',
        governanceHoldReason: 'manual_correction',
        resourceConflictCount: 3,
        notificationFailureCount: 2,
        healthScore: 18,
        healthLevel: 'critical',
        actionPath: '/projects/7',
      }],
      blockedTasks: [{
        taskId: 11,
        title: 'Repair image pipeline',
        projectId: 7,
        projectTitle: 'Delayed imaging study',
        blockedSince: '2026-07-20T08:00:00Z',
        blockedDays: 9,
        deadlineAt: '2026-07-25T08:00:00Z',
        actionPath: '/projects/7',
      }],
      missingReports: [{
        projectId: 7,
        projectTitle: 'Delayed imaging study',
        periodId: 3,
        periodStart: '2026-07-20',
        deadlineAt: '2026-07-27T08:00:00Z',
        missingCount: 2,
        actionPath: '/projects/7/reports',
      }],
      governanceHolds: [{
        projectId: 7,
        projectTitle: 'Delayed imaging study',
        reason: 'manual_correction',
        startedAt: '2026-07-26T08:00:00Z',
        actionPath: '/projects/7',
      }],
      trend: Array.from({ length: 14 }, (_, index) => ({
        date: `2026-07-${String(16 + index).padStart(2, '0')}`,
        resourceConflicts: index === 13 ? 3 : 0,
        notificationFailures: index === 12 ? 2 : 0,
      })),
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })));

    renderWithClient(<MemoryRouter><ProjectHealthPage /></MemoryRouter>);

    expect(await screen.findByRole('heading', { name: 'Project health operations' })).toBeInTheDocument();
    expect(await screen.findByText('50%')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Delayed imaging study' })[0]).toHaveAttribute('href', '/projects/7');
    expect(screen.getByRole('region', { name: 'Operations failure trend' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Long-term blockers' })).toContainElement(screen.getByText('Repair image pipeline'));
    expect(screen.getByRole('region', { name: 'Missing report queue' })).toContainElement(screen.getByText(/2 missing submissions/));
    expect(screen.getByRole('region', { name: 'Governance intervention' })).toContainElement(screen.getByText('manual correction'));
  });
});
