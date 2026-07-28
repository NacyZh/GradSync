import { Plus } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { useI18n } from '@/shared/i18n/I18nProvider';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { DataState } from '@/shared/ui/DataState';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';

import {
  listRisks,
  raiseRisk,
  transitionRisk,
  triageRisk,
  type RiskRecord,
} from './executionApi';

type Member = {
  userId?: number;
  user_id?: number;
  name?: string;
  nickname?: string;
  email?: string;
};

export function RiskRegister({
  projectId,
  members,
}: {
  projectId: number;
  members: Member[];
}) {
  const { t, formatDate } = useI18n();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const query = useQuery({
    queryKey: ['project-risks', projectId],
    queryFn: () => listRisks(projectId),
  });
  const risks = query.data?.results ?? [];
  const selected = risks.find((item) => item.id === selectedId) ?? risks[0];
  if (query.isLoading)
    return <DataState state="loading" message={t('loadingRisks')} />;
  if (query.error)
    return <DataState state="error" message={query.error.message} />;
  const changed = () => query.refetch();
  return (
    <section className="grid min-h-0 gap-4 xl:grid-cols-[minmax(18rem,0.75fr)_minmax(0,1.25fr)]">
      <div className="panel grid h-[min(42rem,75vh)] min-h-[30rem] grid-rows-[auto_1fr] overflow-hidden">
        <header className="mb-3 flex items-center justify-between gap-2">
          <h2>{t('riskRegister')}</h2>
          {query.data?.canRaise ? (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" />
              {t('raiseRisk')}
            </Button>
          ) : null}
        </header>
        <div className="min-h-0 space-y-2 overflow-y-auto">
          {risks.map((risk) => (
            <button
              type="button"
              key={risk.id}
              className={`w-full rounded-md border p-3 text-left ${risk.id === selected?.id ? 'border-primary bg-accent' : ''}`}
              onClick={() => {
                setCreating(false);
                setSelectedId(risk.id);
              }}
            >
              <div className="flex justify-between gap-2">
                <strong>{risk.title}</strong>
                <StatusBadge status={`${risk.severity} / ${risk.state}`} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {risk.reviewDate
                  ? formatDate(risk.reviewDate)
                  : t('notTriaged')}
              </p>
            </button>
          ))}
        </div>
      </div>
      <div className="panel h-[min(42rem,75vh)] min-h-[30rem] overflow-y-auto">
        {creating ? (
          <RaiseRiskForm
            projectId={projectId}
            onDone={() => {
              setCreating(false);
              changed();
            }}
          />
        ) : selected ? (
          <RiskDetail
            projectId={projectId}
            risk={selected}
            members={members}
            canTriage={Boolean(query.data?.canTriage)}
            onChanged={changed}
          />
        ) : (
          <DataState state="empty" message={t('noRisks')} />
        )}
      </div>
    </section>
  );
}

function RaiseRiskForm({
  projectId,
  onDone,
}: {
  projectId: number;
  onDone: () => void;
}) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const mutation = useMutation({
    mutationFn: () =>
      raiseRisk(projectId, {
        title,
        description,
        idempotencyKey: crypto.randomUUID(),
      }),
    onSuccess: () => {
      notify(t('riskRaised'), 'success');
      onDone();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <h2>{t('raiseRisk')}</h2>
      <Input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder={t('title')}
        required
      />
      <Textarea
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder={t('description')}
        required
      />
      <Button type="submit">{t('raiseRisk')}</Button>
    </form>
  );
}

function RiskDetail({
  projectId,
  risk,
  members,
  canTriage,
  onChanged,
}: {
  projectId: number;
  risk: RiskRecord;
  members: Member[];
  canTriage: boolean;
  onChanged: () => void;
}) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const [likelihood, setLikelihood] = useState(risk.likelihood);
  const [impact, setImpact] = useState(risk.impact);
  const [ownerId, setOwnerId] = useState(
    risk.owner?.id ?? Number(members[0]?.userId ?? members[0]?.user_id ?? 0),
  );
  const [treatment, setTreatment] = useState(risk.treatment);
  const [reviewDate, setReviewDate] = useState(risk.reviewDate ?? '');
  const [reason, setReason] = useState('');
  const triage = useMutation({
    mutationFn: () =>
      triageRisk(projectId, risk.id, {
        expectedVersion: risk.version,
        likelihood,
        impact,
        ownerId,
        treatment,
        reviewDate,
        reason,
      }),
    onSuccess: () => {
      notify(t('riskUpdated'), 'success');
      onChanged();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const transition = useMutation({
    mutationFn: (action: string) =>
      transitionRisk(projectId, risk.id, {
        expectedVersion: risk.version,
        action,
        reason,
        ownerId,
        reviewDate,
        idempotencyKey: crypto.randomUUID(),
      }),
    onSuccess: () => {
      notify(t('riskUpdated'), 'success');
      onChanged();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  return (
    <div className="grid gap-4">
      <header>
        <div className="flex justify-between gap-3">
          <h2>{risk.title}</h2>
          <StatusBadge status={`${risk.severity} / ${risk.state}`} />
        </div>
        <p className="mt-2 text-sm">{risk.description}</p>
        <p className="mt-2 text-xs text-muted-foreground">
          {risk.matrixExplanation}
        </p>
      </header>
      {canTriage ? (
        <form
          className="grid gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            triage.mutate();
          }}
        >
          <div className="grid grid-cols-2 gap-2">
            <RiskLevel
              label={t('likelihood')}
              value={likelihood}
              onChange={setLikelihood}
            />
            <RiskLevel
              label={t('impact')}
              value={impact}
              onChange={setImpact}
            />
          </div>
          <select
            className="h-10 rounded-md border bg-background px-3"
            value={ownerId}
            onChange={(event) => setOwnerId(Number(event.target.value))}
          >
            {members.map((member) => {
              const id = Number(member.userId ?? member.user_id);
              return (
                <option key={id} value={id}>
                  {member.nickname || member.name || member.email}
                </option>
              );
            })}
          </select>
          <Textarea
            value={treatment}
            onChange={(event) => setTreatment(event.target.value)}
            placeholder={t('treatment')}
            required
          />
          <Input
            type="date"
            value={reviewDate}
            onChange={(event) => setReviewDate(event.target.value)}
            required
          />
          <Textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder={t('transitionReason')}
            required
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit">{t('saveTriage')}</Button>
            {risk.state !== 'mitigating' ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => transition.mutate('start_mitigation')}
              >
                {t('startMitigation')}
              </Button>
            ) : null}
            {!['accepted', 'resolved'].includes(risk.state) ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => transition.mutate('accept')}
                >
                  {t('acceptRisk')}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => transition.mutate('resolve')}
                >
                  {t('resolveRisk')}
                </Button>
              </>
            ) : (
              <Button
                type="button"
                variant="outline"
                onClick={() => transition.mutate('reopen')}
              >
                {t('reopenRisk')}
              </Button>
            )}
          </div>
        </form>
      ) : null}
      <section>
          <h3>{t('riskRevisionHistory')}</h3>
        <ol className="mt-2 space-y-2">
          {risk.revisions.map((revision) => (
            <li
              key={revision.revisionNumber}
              className="rounded-md border p-2 text-sm"
            >
              <strong>
                #{revision.revisionNumber} {revision.previousState} →{' '}
                {revision.newState}
              </strong>
              <p>{revision.reason}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function RiskLevel({
  label,
  value,
  onChange,
}: {
  label: string;
  value: 'low' | 'medium' | 'high';
  onChange: (value: 'low' | 'medium' | 'high') => void;
}) {
  return (
    <fieldset>
      <legend className="mb-1 text-sm font-bold">{label}</legend>
      <div className="grid grid-cols-3 gap-1">
        {(['low', 'medium', 'high'] as const).map((level) => (
          <Button
            key={level}
            type="button"
            size="sm"
            variant={value === level ? 'default' : 'outline'}
            aria-pressed={value === level}
            onClick={() => onChange(level)}
          >
            {level}
          </Button>
        ))}
      </div>
    </fieldset>
  );
}
