import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { ReviewQueuePage } from '../../src/features/submissions/ReviewQueuePage';
import { ReviewStatusControl } from '../../src/features/submissions/ReviewStatusControl';
import { WeeklyReportHistory } from '../../src/features/submissions/WeeklyReportHistory';
import { renderWithClient } from './test-utils';

describe('submission review UI', () => {
  it('renders review status control', () => {
    renderWithClient(<ReviewStatusControl status="pending_review" />);
    expect(screen.getByLabelText('Review status')).toBeInTheDocument();
  });

  it('renders weekly report history with review status badges and revisions', () => {
    renderWithClient(<WeeklyReportHistory reports={[{ id: 7, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', revision_number: 2, review_status: 'needs_revision' }]} />);
    expect(screen.getByRole('heading', { name: 'Report history' })).toBeInTheDocument();
    expect(screen.getByText(/Revision 2/)).toBeInTheDocument();
    expect(screen.getByText('needs revision')).toBeInTheDocument();
  });

  it('renders production review queue surfaces for reports and comments', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        const value = String(url);
        if (value.includes('/api/projects/1/reports/')) {
          return new Response(JSON.stringify({ results: [{ id: 71, report_week_start: '2026-06-22', completed_work: 'Completed experiments', blockers: 'Waiting for microscope time', next_steps: 'Analyze sample images', revision_number: 2, review_status: 'pending_review', submitted_at: '2026-06-23T08:00:00Z' }] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        if (value.includes('/api/projects/1/comments/')) {
          return new Response(JSON.stringify({ results: [{ id: 91, target_type: 'progress_report', target_id: 71, anchor: 'methods', body: 'Clarify sample count', status: 'open' }] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ results: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    renderWithClient(
      <MemoryRouter initialEntries={['/projects/1/reviews']}>
        <Routes>
          <Route path="/projects/:projectId/reviews" element={<ReviewQueuePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'Review queue' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /Week 2026-06-22/ })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Review queue list' })).toHaveTextContent('Week 2026-06-22');
    expect(screen.getByRole('region', { name: 'Completed work for report 71' })).toHaveTextContent('Completed experiments');
    expect(screen.getByRole('region', { name: 'Blockers for report 71' })).toHaveTextContent('Waiting for microscope time');
    expect(screen.getByRole('region', { name: 'Next steps for report 71' })).toHaveTextContent('Analyze sample images');
    expect(screen.queryByRole('tab', { name: 'Drafts' })).not.toBeInTheDocument();
    expect(await screen.findByText('Clarify sample count')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Submission review' })).toHaveTextContent('Week 2026-06-22');
    expect(screen.getByRole('complementary', { name: 'Inline comments' })).toHaveTextContent('Clarify sample count');
    expect(screen.getByLabelText('Review status')).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it('links inline comments to the selected review queue report', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        const value = String(url);
        if (value.includes('/api/projects/1/reports/')) {
          return new Response(JSON.stringify({
            results: [
              { id: 80, report_week_start: '2026-07-13', completed_work: 'Seeded recent report', blockers: '', next_steps: 'Keep collecting data', revision_number: 1, review_status: 'pending_review' },
              { id: 71, report_week_start: '2026-06-22', completed_work: 'Completed experiments', blockers: '', next_steps: 'Analyze sample images', revision_number: 2, review_status: 'needs_revision' },
            ],
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        if (value.includes('/api/projects/1/comments/')) {
          const body = value.includes('target_id=71')
            ? { results: [{ id: 91, target_type: 'progress_report', target_id: 71, anchor: 'methods', body: 'Clarify sample count', status: 'open' }] }
            : { results: [{ id: 92, target_type: 'progress_report', target_id: 80, anchor: 'summary', body: 'Add latest milestone', status: 'open' }] };
          return new Response(JSON.stringify(body), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ results: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    renderWithClient(
      <MemoryRouter initialEntries={['/projects/1/reviews']}>
        <Routes>
          <Route path="/projects/:projectId/reviews" element={<ReviewQueuePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Add latest milestone')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Week 2026-06-22/ }));
    expect(screen.getByRole('region', { name: 'Submission review' })).toHaveTextContent('Completed experiments');
    expect(await screen.findByText('Clarify sample count')).toBeInTheDocument();
    expect(screen.queryByText('Add latest milestone')).not.toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Inline comments' })).toHaveTextContent('Linked to Week 2026-06-22');
    vi.unstubAllGlobals();
  });
});
