import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DecisionRegister } from '../../src/features/projects/DecisionRegister';
import { RiskRegister } from '../../src/features/projects/RiskRegister';
import { renderWithClient } from './test-utils';

vi.mock('../../src/features/projects/executionApi', async () => {
  const actual = await vi.importActual('../../src/features/projects/executionApi');
  return {
    ...actual,
    listDecisions: vi.fn().mockResolvedValue({
      results: [{
        id: 1,
        projectId: 1,
        title: 'Adopt protocol',
        context: 'Protocol context',
        optionsConsidered: ['A', 'B'],
        outcome: 'A',
        rationale: 'Validated',
        owner: { id: 1, displayName: 'Advisor', role: 'advisor' },
        effectiveDate: '2026-07-28',
        status: 'current',
        publishedBy: { id: 1, displayName: 'Advisor', role: 'advisor' },
        publishedAt: '2026-07-28T00:00:00Z',
      }],
      page: { nextCursor: null },
      canPublish: false,
    }),
    listRisks: vi.fn().mockResolvedValue({
      results: [{
        id: 2,
        projectId: 1,
        title: 'Recruitment delay',
        description: 'Behind plan',
        sourceType: 'manual',
        likelihood: 'medium',
        impact: 'high',
        severity: 'high',
        matrixExplanation: 'medium likelihood and high impact produce high severity.',
        owner: null,
        treatment: '',
        reviewDate: null,
        state: 'raised',
        closureRationale: '',
        version: 1,
        raisedBy: { id: 2, displayName: 'Student', role: 'student' },
        createdAt: '2026-07-28T00:00:00Z',
        updatedAt: '2026-07-28T00:00:00Z',
        revisions: [],
      }],
      page: { nextCursor: null },
      canRaise: true,
      canTriage: false,
    }),
  };
});

describe('project governance records', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows immutable decision detail without edit or delete controls', async () => {
    renderWithClient(<DecisionRegister projectId={1} members={[]} />);
    expect(await screen.findByText('Protocol context')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /supersede/i })).not.toBeInTheDocument();
  });

  it('shows server-derived risk severity without triage controls', async () => {
    renderWithClient(<RiskRegister projectId={1} members={[]} />);
    expect(await screen.findByText(/medium likelihood and high impact/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save triage' })).not.toBeInTheDocument();
  });
});
