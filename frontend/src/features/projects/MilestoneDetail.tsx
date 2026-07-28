import { Archive, CalendarDays } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { DataState } from '@/shared/ui/DataState';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { formatUiDate } from '@/shared/i18n/translate';
import { useI18n } from '@/shared/i18n/I18nProvider';

import type { Milestone } from './executionApi';

type Props = {
  milestone?: Milestone;
  ownerNames: string[];
  canManage: boolean;
  onArchive: () => void;
  isArchiving?: boolean;
};

export function MilestoneDetail({
  milestone,
  ownerNames,
  canManage,
  onArchive,
  isArchiving,
}: Props) {
  const { t } = useI18n();
  if (!milestone) {
    return (
      <DataState
        state="empty"
        title={t('noMilestoneSelected')}
        message={t('noMilestoneSelectedMessage')}
      />
    );
  }
  return (
    <article className="grid min-h-0 content-start gap-5 overflow-y-auto pr-1">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="break-words text-xl font-extrabold">{milestone.title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t('derivedMilestoneStatus')}
          </p>
        </div>
        <StatusBadge status={milestone.status} />
      </header>
      <dl className="grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-bold text-muted-foreground">{t('targetDate')}</dt>
          <dd className="mt-1 inline-flex items-center gap-2">
            <CalendarDays className="h-4 w-4" />
            {formatUiDate(milestone.targetDate)}
          </dd>
        </div>
        <div>
          <dt className="font-bold text-muted-foreground">{t('owners')}</dt>
          <dd className="mt-1 break-words">{ownerNames.join(', ') || t('unavailable')}</dd>
        </div>
        <div>
          <dt className="font-bold text-muted-foreground">{t('requiredDeliverables')}</dt>
          <dd className="mt-1">{milestone.requiredDeliverables}</dd>
        </div>
        <div>
          <dt className="font-bold text-muted-foreground">{t('advisorAccepted')}</dt>
          <dd className="mt-1">{milestone.acceptedDeliverables}</dd>
        </div>
      </dl>
      <section>
        <h3 className="text-sm font-bold text-muted-foreground">{t('description')}</h3>
        <p className="mt-2 whitespace-pre-wrap text-sm">
          {milestone.description || t('noDescriptionProvided')}
        </p>
      </section>
      {canManage && milestone.status !== 'archived' ? (
        <div className="border-t pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={onArchive}
            disabled={isArchiving}
          >
            <Archive className="h-4 w-4" />
            {t('archiveMilestone')}
          </Button>
        </div>
      ) : null}
    </article>
  );
}
