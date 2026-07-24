import { X } from 'lucide-react';

import { formatUiDate } from '@/shared/i18n/translate';
import { Button } from '@/shared/ui/primitives/button';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { useI18n } from '@/shared/i18n/I18nProvider';

import type { AuditEvent } from './api';

export function AuditEventDetail({
  event,
  onClose,
}: {
  event?: AuditEvent;
  onClose?: () => void;
}) {
  const { t } = useI18n();
  return (
    <section
      className="panel min-h-0 overflow-y-auto max-lg:fixed max-lg:inset-x-0 max-lg:bottom-0 max-lg:z-40 max-lg:h-1/2 max-lg:rounded-none max-lg:border-x-0"
      aria-label={t('auditEventDetail')}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2>{t('eventDetail')}</h2>
          <p className="text-sm text-muted-foreground">{t('immutableRedactedEvidence')}</p>
        </div>
        {onClose ? (
          <Button type="button" size="icon" variant="ghost" aria-label={t('closeDetail')} onClick={onClose}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      {event ? (
        <div className="mt-4 grid gap-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={event.outcome} />
            <span>{event.category}</span>
          </div>
          <dl className="grid gap-3">
            <div><dt className="font-bold">{t('event')}</dt><dd className="break-all">{event.eventType}</dd></div>
            <div><dt className="font-bold">{t('summary')}</dt><dd>{event.summary}</dd></div>
            <div><dt className="font-bold">{t('time')}</dt><dd>{event.createdAt ? formatUiDate(event.createdAt, { dateStyle: 'medium', timeStyle: 'medium' }) : '-'}</dd></div>
            <div><dt className="font-bold">{t('correlationId')}</dt><dd className="break-all">{event.correlationId || '-'}</dd></div>
            <div><dt className="font-bold">{t('actorSnapshot')}</dt><dd><pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-muted p-3">{JSON.stringify(event.actorSnapshot ?? {}, null, 2)}</pre></dd></div>
            <div><dt className="font-bold">{t('targetSnapshot')}</dt><dd><pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-muted p-3">{JSON.stringify(event.targetSnapshot ?? {}, null, 2)}</pre></dd></div>
          </dl>
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">{t('selectAuditEvent')}</p>
      )}
    </section>
  );
}
