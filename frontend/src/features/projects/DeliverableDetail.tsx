import { CheckCircle2, Send } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { DataState } from '@/shared/ui/DataState';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { formatUiDate } from '@/shared/i18n/translate';
import { useI18n } from '@/shared/i18n/I18nProvider';

import type { ProjectMaterial } from './api';
import {
  decideDeliverable,
  recommendDeliverable,
  submitDeliverable,
  updateDeliverable,
  type Deliverable,
} from './executionApi';
import {
  DeliverableEvidence,
  type EvidenceDraft,
} from './DeliverableEvidence';

type Props = {
  projectId: number;
  deliverable?: Deliverable;
  materials: ProjectMaterial[];
  onChanged: () => Promise<unknown> | void;
};

export function DeliverableDetail({
  projectId,
  deliverable,
  materials,
  onChanged,
}: Props) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const [progress, setProgress] = useState(0);
  const [workStatus, setWorkStatus] = useState<'planned' | 'in_progress' | 'blocked'>(
    'planned',
  );
  const [blocker, setBlocker] = useState('');
  const [description, setDescription] = useState('');
  const [evidence, setEvidence] = useState<EvidenceDraft[]>([]);
  const [recommendation, setRecommendation] = useState<'accept' | 'return'>('accept');
  const [decision, setDecision] = useState<'accepted' | 'returned'>('accepted');
  const [rationale, setRationale] = useState('');

  useEffect(() => {
    if (!deliverable) return;
    setProgress(deliverable.progressPercent);
    setWorkStatus(
      ['planned', 'in_progress', 'blocked'].includes(deliverable.status)
        ? (deliverable.status as 'planned' | 'in_progress' | 'blocked')
        : 'in_progress',
    );
    setBlocker(deliverable.blockerSummary);
    setDescription('');
    setEvidence([]);
    setRationale('');
  }, [deliverable]);

  const progressMutation = useMutation({
    mutationFn: () =>
      updateDeliverable(projectId, deliverable!.id, {
        expectedVersion: deliverable!.version,
        progressPercent: progress,
        workStatus,
        blockerSummary: blocker,
      }),
    onSuccess: async () => {
      notify(t('deliverableProgressUpdated'), 'success');
      await onChanged();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const submitMutation = useMutation({
    mutationFn: () =>
      submitDeliverable(projectId, deliverable!.id, {
        expectedVersion: deliverable!.version,
        description,
        evidence,
        idempotencyKey: crypto.randomUUID(),
      }),
    onSuccess: async () => {
      notify(t('deliverableRevisionSubmitted'), 'success');
      await onChanged();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const reviewMutation = useMutation({
    mutationFn: () => {
      const revision = deliverable!.revisions[0];
      return recommendDeliverable(projectId, deliverable!.id, {
        revisionId: revision.id,
        recommendation,
        rationale,
        idempotencyKey: crypto.randomUUID(),
      });
    },
    onSuccess: async () => {
      notify(t('reviewRecommendationRecorded'), 'success');
      await onChanged();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const decisionMutation = useMutation({
    mutationFn: () => {
      const revision = deliverable!.revisions[0];
      return decideDeliverable(projectId, deliverable!.id, {
        revisionId: revision.id,
        decision,
        rationale,
        expectedVersion: deliverable!.version,
        idempotencyKey: crypto.randomUUID(),
      });
    },
    onSuccess: async () => {
      notify(t('finalDeliverableDecisionRecorded'), 'success');
      await onChanged();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  if (!deliverable) {
    return (
      <DataState
        state="empty"
        title={t('noDeliverableSelected')}
        message={t('noDeliverableSelectedMessage')}
      />
    );
  }
  const latestRevision = deliverable.revisions[0];
  const canSubmit =
    deliverable.capabilities.canSubmitAssignedDeliverables &&
    !['accepted', 'archived'].includes(deliverable.status);

  return (
    <article className="grid min-h-0 content-start gap-5 overflow-y-auto pr-1">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="break-words text-xl font-extrabold">{deliverable.title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Due {formatUiDate(deliverable.dueDate)}
          </p>
        </div>
        <StatusBadge status={deliverable.status} />
      </header>
      <section className="grid gap-2 text-sm">
          <h3 className="font-bold text-muted-foreground">{t('acceptanceCriteria')}</h3>
        <p className="whitespace-pre-wrap">{deliverable.acceptanceCriteria}</p>
      </section>
      <section className="grid gap-3 border-t pt-4" aria-label="Deliverable progress">
        <h3 className="font-extrabold">{t('progress')}</h3>
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem]">
          <label className="grid gap-1.5 text-sm font-bold">
            {t('progressPercent')}
            <Input
              type="number"
              min={0}
              max={100}
              value={progress}
              onChange={(event) => setProgress(Number(event.target.value))}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-bold">
            {t('workStatus')}
            <Select
              value={workStatus}
              onValueChange={(value) =>
                setWorkStatus(value as 'planned' | 'in_progress' | 'blocked')
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="planned">{t('planned')}</SelectItem>
                <SelectItem value="in_progress">{t('inProgress')}</SelectItem>
                <SelectItem value="blocked">{t('blocked')}</SelectItem>
              </SelectContent>
            </Select>
          </label>
        </div>
        {workStatus === 'blocked' ? (
          <Textarea
            value={blocker}
            onChange={(event) => setBlocker(event.target.value)}
            placeholder={t('describeBlocker')}
            aria-label={t('blockerSummary')}
          />
        ) : null}
        {(deliverable.capabilities.canManageDeliverables ||
          deliverable.capabilities.canSubmitAssignedDeliverables) ? (
          <Button
            className="justify-self-start"
            type="button"
            variant="outline"
            onClick={() => progressMutation.mutate()}
            disabled={progressMutation.isPending}
          >
            <CheckCircle2 className="h-4 w-4" />
            {t('updateProgress')}
          </Button>
        ) : null}
      </section>
      {canSubmit ? (
        <section className="grid gap-3 border-t pt-4" aria-label="Submit deliverable">
          <h3 className="font-extrabold">{t('submitRevision')}</h3>
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={t('describeSubmittedOutput')}
            aria-label={t('submissionDescription')}
          />
          <DeliverableEvidence
            materials={materials}
            value={evidence}
            onChange={setEvidence}
          />
          <Button
            className="justify-self-start"
            type="button"
            onClick={() => submitMutation.mutate()}
            disabled={
              submitMutation.isPending || !description.trim() || evidence.length === 0
            }
          >
            <Send className="h-4 w-4" />
            {t('submitRevision')}
          </Button>
        </section>
      ) : null}
      {latestRevision &&
      (deliverable.capabilities.canRecommendDeliverables ||
        deliverable.capabilities.canDecideDeliverables) ? (
        <section className="grid gap-3 border-t pt-4" aria-label="Deliverable review">
          <h3 className="font-extrabold">
            {t('reviewRevision', { number: latestRevision.revisionNumber })}
          </h3>
          <Textarea
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
            placeholder={t('recordReviewRationale')}
            aria-label={t('reviewRationale')}
          />
          <div className="flex flex-wrap gap-2">
            {deliverable.capabilities.canRecommendDeliverables ? (
              <>
                <Select
                  value={recommendation}
                  onValueChange={(value) =>
                    setRecommendation(value as 'accept' | 'return')
                  }
                >
                  <SelectTrigger className="w-48" aria-label="Reviewer recommendation">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="accept">{t('recommendAcceptance')}</SelectItem>
                    <SelectItem value="return">{t('recommendReturn')}</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => reviewMutation.mutate()}
                  disabled={reviewMutation.isPending || !rationale.trim()}
                >
                  {t('recordRecommendation')}
                </Button>
              </>
            ) : null}
            {deliverable.capabilities.canDecideDeliverables ? (
              <>
                <Select
                  value={decision}
                  onValueChange={(value) =>
                    setDecision(value as 'accepted' | 'returned')
                  }
                >
                  <SelectTrigger className="w-48" aria-label="Advisor final decision">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="accepted">{t('acceptRevision')}</SelectItem>
                    <SelectItem value="returned">{t('returnRevision')}</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  onClick={() => decisionMutation.mutate()}
                  disabled={
                    decisionMutation.isPending ||
                    (decision === 'returned' && !rationale.trim())
                  }
                >
                  {t('finalDecision')}
                </Button>
              </>
            ) : null}
          </div>
        </section>
      ) : null}
      <section className="grid gap-3 border-t pt-4" aria-label="Revision history">
        <h3 className="font-extrabold">{t('revisionHistory')}</h3>
        {deliverable.revisions.length ? (
          <ol className="grid gap-3">
            {deliverable.revisions.map((revision) => (
              <li key={revision.id} className="grid gap-2 rounded-md border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <strong>{t('revisionNumber', { number: revision.revisionNumber })}</strong>
                  <StatusBadge status={revision.state} />
                </div>
                <p className="whitespace-pre-wrap">{revision.descriptionSnapshot}</p>
                <ul className="grid gap-1 text-muted-foreground">
                  {revision.evidence.map((item) => (
                    <li key={item.id}>
                      {item.label} {item.available ? '' : t('unavailableSnapshot')}
                    </li>
                  ))}
                </ul>
                {revision.finalDecision ? (
                  <p>
                    {t('advisorDecisionPrefix')} {revision.finalDecision.decision}
                    {revision.finalDecision.rationale
                      ? ` - ${revision.finalDecision.rationale}`
                      : ''}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted-foreground">{t('noRevisionSubmitted')}</p>
        )}
      </section>
    </article>
  );
}
