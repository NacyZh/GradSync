import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ReportTemplateEditor } from '../../src/features/submissions/ReportTemplateEditor';
import { StructuredReportForm } from '../../src/features/submissions/StructuredReportForm';
import type { ReportTemplateVersion } from '../../src/features/submissions/api';
import { renderWithClient } from './test-utils';

const template: ReportTemplateVersion = {
  id: 1,
  templateId: 1,
  projectId: 1,
  name: 'Weekly progress',
  versionNumber: 1,
  status: 'published',
  version: 2,
  publishedAt: '2026-07-28T00:00:00Z',
  fields: [
    {
      id: 10,
      key: 'completed_work',
      labelEn: 'Completed work',
      labelZh: '已完成工作',
      fieldType: 'long_text',
      required: true,
      order: 0,
      options: [],
      analyticsEnabled: false,
    },
  ],
};

describe('structured reports', () => {
  it('keeps a published template immutable in the editor', () => {
    renderWithClient(
      <ReportTemplateEditor projectId={1} template={template} onChanged={() => undefined} />,
    );
    expect(screen.getByDisplayValue('Completed work')).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Publish' })).not.toBeInTheDocument();
  });

  it('renders fields from the period-locked template', () => {
    renderWithClient(
      <StructuredReportForm
        projectId={1}
        template={template}
        period={{
          id: 2,
          projectId: 1,
          startsOn: '2026-07-27',
          endsOn: '2026-08-03',
          deadlineAt: '2026-08-02T18:00:00Z',
          templateVersionId: 1,
          state: 'open',
          currentUserReportStatus: 'missing',
        }}
        onSubmitted={() => undefined}
      />,
    );
    expect(screen.getByLabelText('Completed work')).toBeRequired();
    expect(screen.getByRole('button', { name: 'Submit report' })).toBeInTheDocument();
  });
});
