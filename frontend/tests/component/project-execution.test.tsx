import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DeliverableDetail } from '../../src/features/projects/DeliverableDetail';
import { DeliverableList } from '../../src/features/projects/DeliverableList';
import { ExecutionMemberPicker } from '../../src/features/projects/ExecutionMemberPicker';
import { MilestoneList } from '../../src/features/projects/MilestoneList';
import type {
  Deliverable,
  Milestone,
} from '../../src/features/projects/executionApi';
import { renderWithClient } from './test-utils';

const milestone: Milestone = {
  id: 1,
  projectId: 1,
  title: 'Validated prototype',
  description: 'Reproducible implementation.',
  targetDate: '2026-08-20',
  ownerIds: [12],
  order: 0,
  status: 'in_progress',
  version: 1,
  requiredDeliverables: 1,
  acceptedDeliverables: 0,
  completedAt: null,
  archivedAt: null,
  createdAt: '2026-07-28T00:00:00Z',
  updatedAt: '2026-07-28T00:00:00Z',
};

function deliverableFor(role: 'student' | 'reviewer' | 'advisor'): Deliverable {
  return {
    id: 4,
    projectId: 1,
    milestoneId: 1,
    title: 'Prototype package',
    description: 'Package and execution notes.',
    acceptanceCriteria: 'Runs from a clean environment.',
    dueDate: '2026-08-18',
    required: true,
    reviewerRequired: true,
    status: role === 'student' ? 'in_progress' : 'under_review',
    progressPercent: 45,
    blockerSummary: '',
    assignees: [{ id: 12, name: 'Student One' }],
    taskIds: [],
    version: 2,
    acceptedRevisionId: null,
    revisions:
      role === 'student'
        ? []
        : [
            {
              id: 9,
              revisionNumber: 1,
              state: 'submitted',
              criteriaSnapshot: 'Runs from a clean environment.',
              descriptionSnapshot: 'Reproducible package.',
              submittedBy: { id: 12, name: 'Student One' },
              submittedAt: '2026-07-28T00:00:00Z',
              evidence: [
                {
                  id: 1,
                  type: 'external_url',
                  sourceId: null,
                  url: 'https://example.test/package',
                  label: 'Package',
                  available: true,
                  sourceTypeSnapshot: 'external_url',
                  sourceIdSnapshot: 'https://example.test/package',
                },
              ],
              recommendations: [],
              finalDecision: null,
            },
          ],
    capabilities: {
      canManageMilestones: role === 'advisor',
      canManageDeliverables: role === 'advisor',
      canSubmitAssignedDeliverables: role === 'student',
      canRecommendDeliverables: role !== 'student',
      canDecideDeliverables: role === 'advisor',
      canPublishDecisions: role === 'advisor',
      canRaiseRisks: true,
      canTriageRisks: role === 'advisor',
    },
  };
}

describe('project execution workspace', () => {
  it('uses bounded selectable milestone and deliverable lists', async () => {
    const user = userEvent.setup();
    const onMilestone = vi.fn();
    const onDeliverable = vi.fn();
    render(
      <div>
        <MilestoneList
          milestones={[milestone]}
          selectedId={null}
          onSelect={onMilestone}
        />
        <DeliverableList
          deliverables={[deliverableFor('student')]}
          selectedId={null}
          onSelect={onDeliverable}
        />
      </div>,
    );
    await user.click(screen.getByRole('button', { name: /Validated prototype/ }));
    await user.click(screen.getByRole('button', { name: /Prototype package/ }));
    expect(onMilestone).toHaveBeenCalledWith(milestone);
    expect(onDeliverable).toHaveBeenCalled();
  });

  it('selects multiple members from an input dropdown', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ExecutionMemberPicker
        label="Assignees"
        members={[
          {
            id: 1,
            userId: 12,
            nickname: 'Student One',
            email: 'student@example.edu',
            role: 'student',
            status: 'active',
          },
        ]}
        value={[]}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole('combobox'));
    await user.type(screen.getByLabelText('Search assignees'), 'Student');
    await user.click(screen.getByRole('option', { name: /Student One/ }));
    expect(onChange).toHaveBeenCalledWith([12]);
  });

  it('keeps reviewer recommendation separate from advisor final decision', () => {
    const { unmount } = renderWithClient(
      <DeliverableDetail
        projectId={1}
        deliverable={deliverableFor('reviewer')}
        materials={[]}
        onChanged={() => undefined}
      />,
    );
    expect(
      screen.getByRole('button', { name: 'Record recommendation' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Final decision' })).not.toBeInTheDocument();

    unmount();
    renderWithClient(
      <DeliverableDetail
        projectId={1}
        deliverable={deliverableFor('advisor')}
        materials={[]}
        onChanged={() => undefined}
      />,
    );
    expect(screen.getByRole('button', { name: 'Final decision' })).toBeInTheDocument();
  });

  it('shows submission controls only to assigned student capability', () => {
    renderWithClient(
      <DeliverableDetail
        projectId={1}
        deliverable={deliverableFor('student')}
        materials={[]}
        onChanged={() => undefined}
      />,
    );
    expect(screen.getByRole('heading', { name: 'Submit revision' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Final decision' })).not.toBeInTheDocument();
  });
});
