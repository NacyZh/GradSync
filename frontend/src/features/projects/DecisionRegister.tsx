import { Plus, Replace } from 'lucide-react';
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
  type DecisionRecord,
  listDecisions,
  publishDecision,
  supersedeDecision,
} from './executionApi';

type Member = {
  userId?: number;
  user_id?: number;
  name?: string;
  nickname?: string;
  email?: string;
  role?: string;
};

export function DecisionRegister({
  projectId,
  members,
}: {
  projectId: number;
  members: Member[];
}) {
  const { t, formatDate } = useI18n();
  const { notify } = useAppFeedback();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const query = useQuery({
    queryKey: ['project-decisions', projectId],
    queryFn: () => listDecisions(projectId),
  });
  const decisions = query.data?.results ?? [];
  const selected =
    decisions.find((item) => item.id === selectedId) ?? decisions[0];
  if (query.isLoading)
    return <DataState state="loading" message={t('loadingDecisions')} />;
  if (query.error)
    return <DataState state="error" message={query.error.message} />;
  return (
    <section className="grid min-h-0 gap-4 xl:grid-cols-[minmax(18rem,0.75fr)_minmax(0,1.25fr)]">
      <div className="panel grid h-[min(42rem,75vh)] min-h-[30rem] grid-rows-[auto_1fr] overflow-hidden">
        <header className="mb-3 flex items-center justify-between gap-2">
          <h2>{t('decisionRegister')}</h2>
          {query.data?.canPublish ? (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" />
              {t('newDecision')}
            </Button>
          ) : null}
        </header>
        <div className="min-h-0 space-y-2 overflow-y-auto">
          {decisions.map((decision) => (
            <button
              type="button"
              key={decision.id}
              className={`w-full rounded-md border p-3 text-left ${decision.id === selected?.id ? 'border-primary bg-accent' : ''}`}
              onClick={() => setSelectedId(decision.id)}
            >
              <div className="flex justify-between gap-2">
                <strong>{decision.title}</strong>
                <StatusBadge status={decision.status} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {formatDate(decision.effectiveDate)}
              </p>
            </button>
          ))}
          {!decisions.length ? (
            <DataState state="empty" message={t('noDecisions')} />
          ) : null}
        </div>
      </div>
      <div className="panel h-[min(42rem,75vh)] min-h-[30rem] overflow-y-auto">
        {creating ? (
          <DecisionForm
            projectId={projectId}
            members={members}
            predecessor={selected}
            onDone={() => {
              setCreating(false);
              query.refetch();
            }}
            onError={(message) => notify(message, 'error')}
          />
        ) : selected ? (
          <div className="grid gap-4">
            <header className="flex items-start justify-between gap-3">
              <div>
                <h2>{selected.title}</h2>
                <p className="text-sm text-muted-foreground">
                  {selected.owner.displayName}
                </p>
              </div>
              {query.data?.canPublish && selected.status === 'current' ? (
                <Button variant="outline" onClick={() => setCreating(true)}>
                  <Replace className="h-4 w-4" />
                  {t('supersede')}
                </Button>
              ) : null}
            </header>
            <DecisionSection title={t('context')} value={selected.context} />
            <DecisionSection
              title={t('optionsConsidered')}
              value={selected.optionsConsidered.join('\n')}
            />
              <DecisionSection
                title={t('governanceOutcome')}
                value={selected.outcome}
              />
            <DecisionSection
              title={t('rationale')}
              value={selected.rationale}
            />
          </div>
        ) : (
          <DataState state="empty" message={t('selectDecision')} />
        )}
      </div>
    </section>
  );
}

function DecisionSection({ title, value }: { title: string; value: string }) {
  return (
    <section>
      <h3 className="text-sm font-bold">{title}</h3>
      <p className="mt-1 whitespace-pre-wrap text-sm">{value}</p>
    </section>
  );
}

function DecisionForm({
  projectId,
  members,
  predecessor,
  onDone,
  onError,
}: {
  projectId: number;
  members: Member[];
  predecessor?: DecisionRecord;
  onDone: () => void;
  onError: (message: string) => void;
}) {
  const { t } = useI18n();
  const advisors = members.filter((member) =>
    ['advisor', 'co_advisor'].includes(member.role ?? ''),
  );
  const [title, setTitle] = useState(predecessor?.title ?? '');
  const [context, setContext] = useState(predecessor?.context ?? '');
  const [options, setOptions] = useState(
    predecessor?.optionsConsidered.join('\n') ?? '',
  );
  const [outcome, setOutcome] = useState('');
  const [rationale, setRationale] = useState('');
  const [ownerId, setOwnerId] = useState(
    Number(advisors[0]?.userId ?? advisors[0]?.user_id ?? 0),
  );
  const [effectiveDate, setEffectiveDate] = useState('');
  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        title,
        context,
        optionsConsidered: options
          .split('\n')
          .map((value) => value.trim())
          .filter(Boolean),
        outcome,
        rationale,
        ownerId,
        effectiveDate,
        idempotencyKey: crypto.randomUUID(),
      };
      return predecessor
        ? supersedeDecision(projectId, predecessor.id, payload)
        : publishDecision(projectId, payload);
    },
    onSuccess: onDone,
    onError: (error) => onError(error.message),
  });
  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <h2>{predecessor ? t('supersedeDecision') : t('newDecision')}</h2>
      <Input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder={t('title')}
        required
      />
      <Textarea
        value={context}
        onChange={(event) => setContext(event.target.value)}
        placeholder={t('context')}
        required
      />
      <Textarea
        value={options}
        onChange={(event) => setOptions(event.target.value)}
        placeholder={t('optionsOnePerLine')}
        required
      />
      <Textarea
        value={outcome}
        onChange={(event) => setOutcome(event.target.value)}
        placeholder={t('governanceOutcome')}
        required
      />
      <Textarea
        value={rationale}
        onChange={(event) => setRationale(event.target.value)}
        placeholder={t('rationale')}
        required
      />
      <select
        className="h-10 rounded-md border bg-background px-3"
        value={ownerId}
        onChange={(event) => setOwnerId(Number(event.target.value))}
      >
        {advisors.map((member) => {
          const id = Number(member.userId ?? member.user_id);
          return (
            <option key={id} value={id}>
              {member.nickname || member.name || member.email}
            </option>
          );
        })}
      </select>
      <Input
        type="date"
        value={effectiveDate}
        onChange={(event) => setEffectiveDate(event.target.value)}
        required
      />
      <Button type="submit" disabled={mutation.isPending}>
        {predecessor ? t('publishSuccessor') : t('publishDecision')}
      </Button>
    </form>
  );
}
