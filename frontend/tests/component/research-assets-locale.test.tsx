import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DuplicateReviewPanel } from '../../src/features/library/DuplicateReviewPanel';
import { PaperDetailPanel } from '../../src/features/library/PaperDetailPanel';
import { PaperFilters } from '../../src/features/library/PaperFilters';
import { I18nProvider, useI18n } from '../../src/features/i18n/I18nProvider';
import { messagesEn } from '../../src/data/locale/messages.en';
import { messagesZh } from '../../src/data/locale/messages.zh';
import { CodeArtifactVersionPanel } from '../../src/features/repositories/CodeArtifactVersionPanel';
import { DownloadStatus } from '../../src/shared/ui/DownloadStatus';
import { renderWithClient } from './test-utils';

describe('research assets and locale UI', () => {
  it('loads locale catalogs from the static data boundary', () => {
    expect(messagesEn.paperLibrary).toBe('Paper library');
    expect(messagesZh.paperLibrary).toBe('论文库');
    expect(messagesEn.paperLibraryDownloadSelectedPaper).toBe('Download selected paper');
    expect(messagesZh.paperLibraryDownloadSelectedPaper).toBe('下载已选论文');
  });

  it('covers paper-library strings in both locale catalogs without Chinese in English values', () => {
    const paperLibraryKeys = [
      'paperLibrary',
      'paperLibraryDescription',
      'paperLibraryImportDownloadRegion',
      'paperLibrarySearchDisplayRegion',
      'paperLibrarySearchPlaceholder',
      'paperLibrarySearchResults',
      'paperLibraryLoadingTitle',
      'paperLibraryUnavailableTitle',
      'paperLibraryEmptyTitle',
      'paperLibraryEmptyDefault',
      'paperLibraryEmptyFilteredPrefix',
      'paperLibrarySelectedPaper',
      'paperLibrarySelectedPaperDetails',
      'paperLibrarySelectBeforeDownload',
      'paperLibraryMetadataAfterSelection',
      'paperLibraryImportPdf',
      'paperLibraryPdfFile',
      'paperLibraryImportPdfButton',
      'paperLibraryProcessingPdf',
      'paperLibrarySelectedPdfPrefix',
      'paperLibraryAcceptedPrefix',
      'paperLibraryDuplicatePrefix',
      'paperLibraryMaintainerReviewRequired',
      'paperLibraryRejectedPrefix',
      'paperLibraryFailedPrefix',
      'paperLibraryUploadRejected',
      'paperLibraryProcessingFailed',
      'paperLibraryUploadLimitExceededPrefix',
      'paperLibraryUploadLimitExceededSuffix',
      'paperLibraryRename',
      'paperLibraryDelete',
      'paperLibraryNewTitle',
      'paperLibrarySaveTitle',
      'paperLibraryCancel',
      'paperLibraryDeleteReason',
      'paperLibraryConfirmDelete',
      'paperLibraryDeleteDescription',
      'paperLibraryInPageViewer',
      'paperLibraryViewerAvailable',
      'paperLibraryViewerUnavailable',
      'paperLibraryUnknownAuthors',
      'paperLibraryUnknownYear',
      'paperLibraryOriginalTitle',
      'paperLibraryVenue',
      'paperLibraryDoi',
      'paperLibraryKeywords',
      'paperLibraryNoKeywords',
      'paperLibraryTitleSource',
      'paperLibraryChecksum',
      'paperLibraryUnspecified',
      'paperLibraryUnavailableValue',
      'paperLibraryDownloadStarted',
    ] as const;

    const enCatalog = messagesEn as Record<string, string | undefined>;
    const zhCatalog = messagesZh as Record<string, string | undefined>;
    for (const key of paperLibraryKeys) {
      expect(enCatalog[key]).toBeTruthy();
      expect(zhCatalog[key]).toBeTruthy();
      expect(enCatalog[key]).not.toMatch(/[\u3400-\u9fff]/);
    }
  });

  it('renders paper search and duplicate review states', async () => {
    const onChange = vi.fn();
    renderWithClient(
      <>
        <PaperFilters value="" onChange={onChange} />
        <DuplicateReviewPanel
          job={{
            id: '1',
            status: 'duplicate',
            requestedBy: '10',
            userMessage: 'Duplicate paper detected',
            acceptedPaper: null,
            duplicatePaper: {
              id: 'paper-1',
              projectId: '1',
              title: 'Duplicate Paper',
              canonicalTitle: 'Duplicate Paper',
              authors: ['Ada Lovelace'],
              visibility: 'group_wide',
              status: 'active',
            },
            duplicateDetection: {
              decision: 'duplicate_metadata_strong_match',
              matchBasis: 'normalized_title_author_year',
              candidatePaperId: 'paper-1',
              similarityScore: 1,
              reviewStatus: 'none',
            },
          }}
        />
      </>,
    );

    await userEvent.type(screen.getByPlaceholderText(/Search title/), 'graph');
    expect(onChange).toHaveBeenCalled();
    expect(screen.getByText('Duplicate paper detected')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View existing paper' })).toBeInTheDocument();
  });

  it('renders paper detail download states', () => {
    renderWithClient(
      <PaperDetailPanel
        projectId={1}
        variant="download"
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
    expect(screen.getByRole('button', { name: 'Download Graph Neural Methods' })).toBeEnabled();
  });

  it('renders code version detail and download status', () => {
    renderWithClient(
      <>
        <CodeArtifactVersionPanel
          artifact={{
            id: '1',
            projectId: '1',
            name: 'Analysis Toolkit',
            status: 'active',
            latestVersion: {
              id: '2',
              artifactId: '1',
              projectId: '1',
              versionLabel: 'v1',
              filename: 'analysis-toolkit.zip',
              checksumSha256: 'b',
              status: 'active',
            },
          }}
        />
        <DownloadStatus descriptor={{ filename: 'analysis-toolkit.zip', deliveryMode: 'direct_response' }} />
      </>,
    );
    expect(screen.getByText('Analysis Toolkit')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('analysis-toolkit.zip');
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
