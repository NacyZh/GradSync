import { CalendarClock, Check, ExternalLink, Pencil, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Button } from '../../shared/ui/primitives/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../shared/ui/primitives/dialog';
import { formatUiDate } from '../../shared/i18n/translate';
import { Label } from '../../shared/ui/primitives/label';
import type { CalendarOccurrence } from './api';
import { formatOccurrenceTime, listScheduleRevisions, occurrenceStart, retrieveScheduleDeliveryStatus } from './api';

type Props = {
  occurrence: CalendarOccurrence | null;
  upcoming?: CalendarOccurrence[];
  onSelect?: (occurrence: CalendarOccurrence) => void;
  onClose?: () => void;
  onEdit?: (scope: 'occurrence' | 'future' | 'series', occurrenceKey: string) => void;
  onComplete?: (scope: 'occurrence' | 'future' | 'series', occurrenceKey: string) => void;
  onDelete?: (scope: 'occurrence' | 'future' | 'series', occurrenceKey: string) => void;
  onCancel?: (scope: 'occurrence' | 'future' | 'series', occurrenceKey: string) => void;
};

export function ScheduleDetailPanel({ occurrence, upcoming = [], onSelect, onClose, onEdit, onComplete, onDelete, onCancel }: Props) {
  const [pendingAction, setPendingAction] = useState<'edit' | 'complete' | 'delete' | 'cancel' | null>(null);
  const [changeScope, setChangeScope] = useState<'occurrence' | 'future' | 'series'>('series');
  const scheduleId = occurrence?.sourceType === 'schedule' ? occurrence.scheduleId : null;
  const revisions = useQuery({
    queryKey: ['schedule-revisions', scheduleId],
    queryFn: () => listScheduleRevisions(scheduleId as number),
    enabled: Boolean(scheduleId && occurrence?.scope === 'group'),
  });
  const delivery = useQuery({
    queryKey: ['schedule-delivery', scheduleId],
    queryFn: () => retrieveScheduleDeliveryStatus(scheduleId as number),
    enabled: Boolean(scheduleId && occurrence?.capabilities.canViewDeliveryStatus),
  });
  if (!occurrence) {
    const visibleUpcoming = [...upcoming]
      .sort((left, right) => occurrenceStart(left).getTime() - occurrenceStart(right).getTime())
      .slice(0, 7);
    return (
      <aside className="calendar-detail" aria-label="Schedule details" data-empty="true">
        <div className="calendar-detail-title">
          <div>
            <span className="calendar-detail-kicker"><CalendarClock className="h-4 w-4" aria-hidden="true" /> Next in this period</span>
            <h2>Upcoming</h2>
          </div>
        </div>
        {visibleUpcoming.length ? (
          <ol className="calendar-upcoming-list">
            {visibleUpcoming.map((item) => (
              <li key={item.occurrenceId}>
                <button type="button" onClick={() => onSelect?.(item)} aria-label={`${item.title}, ${formatOccurrenceTime(item)}`}>
                  <span className={`calendar-source-mark source-${item.sourceType}`} aria-hidden="true" />
                  <span><strong>{item.title}</strong><small>{formatUiDate(occurrenceStart(item), { month: 'short', day: 'numeric' })} · {formatOccurrenceTime(item)}</small></span>
                </button>
              </li>
            ))}
          </ol>
        ) : <p className="calendar-empty">No upcoming items in this period.</p>}
      </aside>
    );
  }
  const systemOwned = occurrence.sourceType !== 'schedule';
  return (
    <aside className="calendar-detail" aria-label="Schedule details">
      <div className="calendar-detail-title">
        <div className="calendar-detail-heading">
          <span className={`calendar-source-label source-${occurrence.sourceType}`}>{sourceLabel(occurrence.sourceType)}</span>
          <span className="status-badge">{occurrence.status.replaceAll('_', ' ')}</span>
        </div>
        {onClose ? (
          <Button type="button" variant="ghost" size="icon" aria-label="Close schedule details" onClick={onClose}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      <h2>{occurrence.title}</h2>
      <dl>
        <div><dt>Date</dt><dd>{formatUiDate(occurrenceStart(occurrence), { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</dd></div>
        <div><dt>Time</dt><dd>{formatOccurrenceTime(occurrence)}</dd></div>
        <div><dt>Timezone</dt><dd>{occurrence.timezone}</dd></div>
      </dl>
      {occurrence.description ? <p>{occurrence.description}</p> : null}
      {systemOwned ? <p className="calendar-readonly">Read-only project data</p> : null}
      <div className="calendar-detail-actions">
        {occurrence.capabilities.canEdit && onEdit ? <Button type="button" variant="outline" onClick={() => setPendingAction('edit')}><Pencil className="h-4 w-4" aria-hidden="true" /> Edit</Button> : null}
        {occurrence.capabilities.canEdit && occurrence.status !== 'completed' && onComplete ? <Button type="button" variant="outline" onClick={() => setPendingAction('complete')}><Check className="h-4 w-4" aria-hidden="true" /> Complete</Button> : null}
        {occurrence.capabilities.canDelete && onDelete ? <Button type="button" variant="destructive" onClick={() => setPendingAction('delete')}><Trash2 className="h-4 w-4" aria-hidden="true" /> Delete</Button> : null}
        {occurrence.capabilities.canCancel && onCancel && occurrence.status !== 'cancelled' ? <Button type="button" variant="destructive" onClick={() => setPendingAction('cancel')}><X className="h-4 w-4" aria-hidden="true" /> Cancel schedule</Button> : null}
        {occurrence.actionPath ? (
          <Button asChild variant="outline">
            <Link to={occurrence.actionPath}>Open source <ExternalLink className="h-4 w-4" aria-hidden="true" /></Link>
          </Button>
        ) : null}
      </div>
      {delivery.data ? (
        <section className="schedule-delivery-summary" aria-label="Delivery status">
          <h3>Delivery</h3>
          <dl>
            <div><dt>Active recipients</dt><dd>{delivery.data.resolvedRecipients.active}</dd></div>
            <div><dt>In-app</dt><dd>{delivery.data.notifications.inAppCreated}</dd></div>
            <div><dt>Email</dt><dd>{delivery.data.notifications.emailSent}/{delivery.data.notifications.emailQueued + delivery.data.notifications.emailSent}</dd></div>
          </dl>
        </section>
      ) : null}
      {revisions.data?.results.length ? (
        <section className="schedule-revision-history" aria-label="Revision history">
          <h3>Revision history</h3>
          <ol>{revisions.data.results.slice(0, 5).map((revision) => (
            <li key={revision.revisionNumber}>
              <strong>{revision.changeType.replaceAll('_', ' ')}</strong>
              <span>{revision.actor.name} · {formatUiDate(revision.createdAt, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
            </li>
          ))}</ol>
        </section>
      ) : null}
      <Dialog open={Boolean(pendingAction)} onOpenChange={(open) => { if (!open) setPendingAction(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{pendingAction === 'delete' ? 'Delete schedule' : pendingAction === 'cancel' ? 'Cancel group schedule' : pendingAction === 'complete' ? 'Complete schedule' : 'Edit schedule'}</DialogTitle>
            <DialogDescription>Choose which part of this schedule is affected.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-1.5">
            <Label htmlFor="schedule-change-scope">Change scope</Label>
            <select id="schedule-change-scope" className="schedule-native-select" value={changeScope} onChange={(event) => setChangeScope(event.target.value as typeof changeScope)}>
              <option value="occurrence">This occurrence</option>
              <option value="future">This and future occurrences</option>
              <option value="series">Entire series</option>
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPendingAction(null)}>Back</Button>
            <Button type="button" variant={pendingAction === 'delete' ? 'destructive' : 'default'} onClick={() => {
              const key = occurrenceKey(occurrence);
              if (pendingAction === 'edit') onEdit?.(changeScope, key);
              if (pendingAction === 'complete') onComplete?.(changeScope, key);
              if (pendingAction === 'delete') onDelete?.(changeScope, key);
              if (pendingAction === 'cancel') onCancel?.(changeScope, key);
              setPendingAction(null);
            }}>{pendingAction === 'delete' ? 'Confirm delete' : pendingAction === 'cancel' ? 'Confirm cancellation' : pendingAction === 'complete' ? 'Confirm complete' : 'Continue'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  );
}

function occurrenceKey(occurrence: CalendarOccurrence) {
  return occurrence.occurrenceId.split(':').slice(2).join(':');
}

function sourceLabel(source: CalendarOccurrence['sourceType']) {
  return source.charAt(0).toUpperCase() + source.slice(1);
}
