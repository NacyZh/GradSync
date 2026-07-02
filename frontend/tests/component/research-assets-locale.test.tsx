import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DuplicateReviewPanel } from '../../src/features/library/DuplicateReviewPanel';
import { PaperDetailPanel } from '../../src/features/library/PaperDetailPanel';
import { PaperFilters } from '../../src/features/library/PaperFilters';
import { I18nProvider, useI18n } from '../../src/features/i18n/I18nProvider';
import { CodeArtifactVersionPanel } from '../../src/features/repositories/CodeArtifactVersionPanel';
import { DownloadStatus } from '../../src/shared/ui/DownloadStatus';
import { renderWithClient } from './test-utils';

describe('research assets and locale UI', () => {
  it('renders paper search and duplicate review states', async () => {
    const onChange = vi.fn();
    renderWithClient(
      <>
        <PaperFilters value="" onChange={onChange} />
        <DuplicateReviewPanel
          batch={{
            id: '1',
            projectId: '1',
            status: 'staged',
            totalItems: 2,
            acceptedCount: 1,
            duplicateCount: 1,
            errorCount: 0,
            results: [{ status: 'duplicate', duplicateReason: 'doi', message: 'Duplicate paper detected' }],
          }}
        />
      </>,
    );

    await userEvent.type(screen.getByPlaceholderText(/Search title/), 'graph');
    expect(onChange).toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('Duplicate paper detected');
  });

  it('renders paper detail download states', () => {
    renderWithClient(
      <PaperDetailPanel
        projectId={1}
        paper={{
          id: '1',
          projectId: '1',
          title: 'Graph Neural Methods',
          authors: ['Lin Chen'],
          doi: '10.1000/graph',
          status: 'active',
          attachments: [{ id: '1', filename: 'graph.pdf', checksumSha256: 'a', status: 'active' }],
        }}
      />,
    );
    expect(screen.getByText('Graph Neural Methods')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download' })).toBeEnabled();
  });

  it('renders code version detail and download status', () => {
    renderWithClient(
      <>
        <CodeArtifactVersionPanel
          artifact={{
            id: '1',
            projectId: '1',
            name: 'Simulator',
            status: 'active',
            latestVersion: {
              id: '2',
              artifactId: '1',
              projectId: '1',
              versionLabel: 'v1',
              filename: 'sim.zip',
              checksumSha256: 'b',
              status: 'active',
            },
          }}
        />
        <DownloadStatus descriptor={{ filename: 'sim.zip', deliveryMode: 'direct_response' }} />
      </>,
    );
    expect(screen.getByText('Simulator')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('sim.zip');
  });

  it('falls back to localized message catalogs', () => {
    function Probe() {
      const { t } = useI18n();
      return <span>{t('paperLibrary')}</span>;
    }
    renderWithClient(
      <I18nProvider locale="zh">
        <Probe />
      </I18nProvider>,
    );
    expect(screen.getByText('论文库')).toBeInTheDocument();
  });
});
