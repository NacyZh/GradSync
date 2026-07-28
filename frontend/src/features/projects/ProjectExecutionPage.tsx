import { Flag, Gavel, PackageCheck, Plus, Search, TriangleAlert } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useSearchParams, useParams } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/ui/primitives/tabs';
import { DataState } from '@/shared/ui/DataState';
import { PageShell } from '@/shared/ui/PageShell';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { useI18n } from '@/shared/i18n/I18nProvider';

import { getProject, listProjectMaterials } from './api';
import { DeliverableDetail } from './DeliverableDetail';
import { DeliverableList } from './DeliverableList';
import { ExecutionMemberPicker } from './ExecutionMemberPicker';
import {
  archiveMilestone,
  createDeliverable,
  createMilestone,
  getExecutionSummary,
  listDeliverables,
  listMilestones,
  type Deliverable,
  type Milestone,
} from './executionApi';
import { MilestoneDetail } from './MilestoneDetail';
import { MilestoneList } from './MilestoneList';
import { useProjectLiveRefresh } from './useProjectLiveRefresh';
import { DecisionRegister } from './DecisionRegister';
import { RiskRegister } from './RiskRegister';

type WorkspaceTab = 'milestones' | 'deliverables' | 'decisions' | 'risks';

export function ProjectExecutionPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const [searchParams, setSearchParams] = useSearchParams();
  const { notify, confirm } = useAppFeedback();
  const { t } = useI18n();
  const [tab, setTab] = useState<WorkspaceTab>(
    searchParams.get('deliverable') ? 'deliverables' : 'milestones',
  );
  const [query, setQuery] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [selectedMilestoneId, setSelectedMilestoneId] = useState<number | null>(
    Number(searchParams.get('milestone')) || null,
  );
  const [selectedDeliverableId, setSelectedDeliverableId] = useState<number | null>(
    Number(searchParams.get('deliverable')) || null,
  );
  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId),
    enabled: Boolean(projectId),
  });
  const summaryQuery = useQuery({
    queryKey: ['project-execution', projectId],
    queryFn: () => getExecutionSummary(projectId),
    enabled: Boolean(projectId),
  });
  const milestonesQuery = useQuery({
    queryKey: ['project-milestones', projectId, query],
    queryFn: () => listMilestones(projectId, { q: query, pageSize: 100 }),
    enabled: Boolean(projectId),
  });
  const deliverablesQuery = useQuery({
    queryKey: ['project-deliverables', projectId, query],
    queryFn: () => listDeliverables(projectId, { q: query, pageSize: 100 }),
    enabled: Boolean(projectId),
  });
  const materialsQuery = useQuery({
    queryKey: ['projectMaterials', projectId, 'execution-evidence'],
    queryFn: () => listProjectMaterials(projectId),
    enabled: Boolean(projectId),
  });
  const liveRefresh = useProjectLiveRefresh(
    projectId,
    projectQuery.data?.latestEventId,
  );
  const milestones = useMemo(
    () => milestonesQuery.data?.results ?? [],
    [milestonesQuery.data?.results],
  );
  const deliverables = useMemo(
    () => deliverablesQuery.data?.results ?? [],
    [deliverablesQuery.data?.results],
  );
  const selectedMilestone =
    milestones.find((item) => item.id === selectedMilestoneId) ?? milestones[0];
  const selectedDeliverable =
    deliverables.find((item) => item.id === selectedDeliverableId) ?? deliverables[0];
  const capabilities = summaryQuery.data?.capabilities;

  useEffect(() => {
    if (!selectedMilestoneId && milestones[0]) setSelectedMilestoneId(milestones[0].id);
  }, [milestones, selectedMilestoneId]);
  useEffect(() => {
    if (!selectedDeliverableId && deliverables[0]) {
      setSelectedDeliverableId(deliverables[0].id);
    }
  }, [deliverables, selectedDeliverableId]);

  const memberNames = useMemo(
    () =>
      new Map(
        (projectQuery.data?.memberships ?? []).map((member) => [
          member.userId ?? member.user_id ?? 0,
          member.nickname || member.name || member.email || 'Unavailable',
        ]),
      ),
    [projectQuery.data?.memberships],
  );

  async function refreshExecution() {
    await Promise.all([
      summaryQuery.refetch(),
      milestonesQuery.refetch(),
      deliverablesQuery.refetch(),
    ]);
  }

  function selectMilestone(milestone: Milestone) {
    setSelectedMilestoneId(milestone.id);
    setSearchParams({ milestone: String(milestone.id) }, { replace: true });
  }

  function selectDeliverable(deliverable: Deliverable) {
    setSelectedDeliverableId(deliverable.id);
    setSearchParams({ deliverable: String(deliverable.id) }, { replace: true });
  }

  const archiveMutation = useMutation({
    mutationFn: () =>
      archiveMilestone(projectId, selectedMilestone!.id, selectedMilestone!.version),
    onSuccess: async () => {
      notify(t('milestoneArchived'), 'success');
      setSelectedMilestoneId(null);
      await refreshExecution();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  async function onArchiveMilestone() {
    if (!selectedMilestone) return;
    const accepted = await confirm({
      title: t('archiveMilestoneQuestion'),
      message: t('archiveMilestoneMessage'),
      actionLabel: t('archiveMilestone'),
    });
    if (accepted) archiveMutation.mutate();
  }

  if (
    projectQuery.isLoading ||
    summaryQuery.isLoading ||
    milestonesQuery.isLoading ||
    deliverablesQuery.isLoading
  ) {
    return (
      <DataState
        state="loading"
        title={t('loadingExecutionWorkspace')}
        message={t('loadingMilestonesDeliverables')}
      />
    );
  }
  const error =
    projectQuery.error ||
    summaryQuery.error ||
    milestonesQuery.error ||
    deliverablesQuery.error;
  if (error) {
    return (
      <DataState
        state="error"
        title={t('executionWorkspaceUnavailable')}
        message={error.message}
      />
    );
  }

  return (
    <PageShell
      title={t('projectExecution')}
      description={t('projectExecutionDescription')}
      actions={
        (tab === 'milestones' && capabilities?.canManageMilestones)
        || (tab === 'deliverables' && capabilities?.canManageDeliverables) ? (
          <Button type="button" onClick={() => setShowCreate((current) => !current)}>
            <Plus className="h-4 w-4" />
            {showCreate
              ? t('closeForm')
              : tab === 'milestones'
                ? t('newMilestone')
                : t('newDeliverable')}
          </Button>
        ) : undefined
      }
    >
      {liveRefresh.state === 'stale' ? (
        <DataState
          state="warning"
          title={t('executionDataStale')}
          message={t('executionDataStaleMessage')}
        />
      ) : null}
      <section className="grid gap-3 sm:grid-cols-3" aria-label="Execution summary">
        <SummaryMetric
          label={t('openMilestones')}
          value={sumCounts(summaryQuery.data?.milestoneCounts, [
            'planned',
            'in_progress',
            'at_risk',
            'blocked',
            'overdue',
          ])}
        />
        <SummaryMetric
          label={t('deliverablesAwaitingAcceptance')}
          value={sumCounts(summaryQuery.data?.deliverableCounts, [
            'submitted',
            'under_review',
            'changes_requested',
          ])}
        />
        <SummaryMetric
          label={t('pendingActionItems')}
          value={summaryQuery.data?.unresolvedActions ?? 0}
        />
      </section>
      <Tabs
        value={tab}
        onValueChange={(value) => {
          setTab(value as WorkspaceTab);
          setShowCreate(false);
        }}
      >
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 overflow-x-auto pb-1">
            <TabsList>
              <TabsTrigger value="milestones">
                <Flag className="mr-2 h-4 w-4" />
                {t('milestones')}
              </TabsTrigger>
              <TabsTrigger value="deliverables">
                <PackageCheck className="mr-2 h-4 w-4" />
                {t('deliverables')}
              </TabsTrigger>
              <TabsTrigger value="decisions">
                <Gavel className="mr-2 h-4 w-4" />
                {t('decisions')}
              </TabsTrigger>
              <TabsTrigger value="risks">
                <TriangleAlert className="mr-2 h-4 w-4" />
                {t('risks')}
              </TabsTrigger>
            </TabsList>
          </div>
          {tab === 'milestones' || tab === 'deliverables' ? <label className="relative block w-full sm:max-w-xs">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={
                tab === 'milestones' ? t('searchMilestones') : t('searchDeliverables')
              }
              aria-label={
                tab === 'milestones' ? t('searchMilestones') : t('searchDeliverables')
              }
              className="pl-9"
            />
          </label> : null}
        </div>
        {showCreate ? (
          tab === 'milestones' ? (
            <MilestoneCreateForm
              projectId={projectId}
              members={projectQuery.data?.memberships ?? []}
              onCreated={async (milestone) => {
                setShowCreate(false);
                setSelectedMilestoneId(milestone.id);
                await refreshExecution();
              }}
            />
          ) : (
            <DeliverableCreateForm
              projectId={projectId}
              milestones={milestones}
              members={projectQuery.data?.memberships ?? []}
              onCreated={async (deliverable) => {
                setShowCreate(false);
                setSelectedDeliverableId(deliverable.id);
                await refreshExecution();
              }}
            />
          )
        ) : null}
        <TabsContent value="milestones">
          <section className="grid min-h-0 gap-4 xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]">
            <div className="panel grid h-[min(38rem,70vh)] min-h-[28rem] grid-rows-[auto_1fr] overflow-hidden">
              <header className="mb-3 flex items-center justify-between gap-2">
                <h2>{t('milestones')}</h2>
                <StatusBadge status={`${milestones.length} visible`} />
              </header>
              {milestones.length ? (
                <MilestoneList
                  milestones={milestones}
                  selectedId={selectedMilestone?.id ?? null}
                  onSelect={selectMilestone}
                />
              ) : (
                <DataState
                  state="empty"
                  title={t('noMilestones')}
                  message={t('noMilestonesMessage')}
                />
              )}
            </div>
            <div className="panel h-[min(38rem,70vh)] min-h-[28rem] overflow-hidden">
              <MilestoneDetail
                milestone={selectedMilestone}
                ownerNames={(selectedMilestone?.ownerIds ?? []).map(
                  (id) => memberNames.get(id) ?? `User ${id}`,
                )}
                canManage={Boolean(capabilities?.canManageMilestones)}
                onArchive={onArchiveMilestone}
                isArchiving={archiveMutation.isPending}
              />
            </div>
          </section>
        </TabsContent>
        <TabsContent value="deliverables">
          <section className="grid min-h-0 gap-4 xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]">
            <div className="panel grid h-[min(42rem,75vh)] min-h-[30rem] grid-rows-[auto_1fr] overflow-hidden">
              <header className="mb-3 flex items-center justify-between gap-2">
                <h2>{t('deliverables')}</h2>
                <StatusBadge status={`${deliverables.length} visible`} />
              </header>
              {deliverables.length ? (
                <DeliverableList
                  deliverables={deliverables}
                  selectedId={selectedDeliverable?.id ?? null}
                  onSelect={selectDeliverable}
                />
              ) : (
                <DataState
                  state="empty"
                  title={t('noDeliverables')}
                  message={t('noDeliverablesMessage')}
                />
              )}
            </div>
            <div className="panel h-[min(42rem,75vh)] min-h-[30rem] overflow-hidden">
              <DeliverableDetail
                projectId={projectId}
                deliverable={selectedDeliverable}
                materials={materialsQuery.data?.results ?? []}
                onChanged={refreshExecution}
              />
            </div>
          </section>
        </TabsContent>
        <TabsContent value="decisions">
          <DecisionRegister
            projectId={projectId}
            members={projectQuery.data?.memberships ?? []}
          />
        </TabsContent>
        <TabsContent value="risks">
          <RiskRegister
            projectId={projectId}
            members={projectQuery.data?.memberships ?? []}
          />
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-card px-4 py-3">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-extrabold">{value}</p>
    </div>
  );
}

function sumCounts(counts: Record<string, number> | undefined, states: string[]) {
  return states.reduce((total, state) => total + (counts?.[state] ?? 0), 0);
}

type Member = NonNullable<Awaited<ReturnType<typeof getProject>>['memberships']>[number];

function MilestoneCreateForm({
  projectId,
  members,
  onCreated,
}: {
  projectId: number;
  members: Member[];
  onCreated: (milestone: Milestone) => Promise<void>;
}) {
  const { notify } = useAppFeedback();
  const { t } = useI18n();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [ownerIds, setOwnerIds] = useState<number[]>([]);
  const mutation = useMutation({
    mutationFn: () =>
      createMilestone(projectId, { title, description, targetDate, ownerIds }),
    onSuccess: async (milestone) => {
      notify(t('milestoneCreated'), 'success');
      await onCreated(milestone);
    },
    onError: (error) => notify(error.message, 'error'),
  });
  return (
    <form
      className="panel my-4 grid gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <h2>{t('newMilestone')}</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="grid gap-1.5 text-sm font-bold">
          {t('title')}
          <Input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </label>
        <label className="grid gap-1.5 text-sm font-bold">
          {t('targetDate')}
          <Input
            type="date"
            value={targetDate}
            onChange={(event) => setTargetDate(event.target.value)}
            required
          />
        </label>
      </div>
      <label className="grid gap-1.5 text-sm font-bold">
        {t('description')}
        <Textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </label>
      <ExecutionMemberPicker
        label={t('milestoneOwners')}
        members={members}
        value={ownerIds}
        onChange={setOwnerIds}
      />
      <Button
        className="justify-self-start"
        type="submit"
        disabled={mutation.isPending || !title.trim() || !targetDate || !ownerIds.length}
      >
        {t('createMilestone')}
      </Button>
    </form>
  );
}

function DeliverableCreateForm({
  projectId,
  milestones,
  members,
  onCreated,
}: {
  projectId: number;
  milestones: Milestone[];
  members: Member[];
  onCreated: (deliverable: Deliverable) => Promise<void>;
}) {
  const { notify } = useAppFeedback();
  const { t } = useI18n();
  const [milestoneId, setMilestoneId] = useState(milestones[0]?.id ?? 0);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [assigneeIds, setAssigneeIds] = useState<number[]>([]);
  const [reviewerIds, setReviewerIds] = useState<number[]>([]);
  const [reviewerRequired, setReviewerRequired] = useState(false);
  const mutation = useMutation({
    mutationFn: () =>
      createDeliverable(projectId, {
        milestoneId,
        title,
        description,
        acceptanceCriteria,
        dueDate,
        required: true,
        assigneeIds,
        reviewerRequired,
        reviewerIds,
      }),
    onSuccess: async (deliverable) => {
      notify(t('deliverableCreated'), 'success');
      await onCreated(deliverable);
    },
    onError: (error) => notify(error.message, 'error'),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }
  return (
    <form className="panel my-4 grid gap-4" onSubmit={submit}>
      <h2>{t('newDeliverable')}</h2>
      {!milestones.length ? (
        <DataState
          state="warning"
          title={t('milestoneRequired')}
          message={t('milestoneRequiredMessage')}
        />
      ) : (
        <>
          <label className="grid gap-1.5 text-sm font-bold">
            {t('milestone')}
            <select
              className="min-h-10 rounded-md border bg-background px-3"
              value={milestoneId}
              onChange={(event) => setMilestoneId(Number(event.target.value))}
            >
              {milestones.map((milestone) => (
                <option key={milestone.id} value={milestone.id}>
                  {milestone.title}
                </option>
              ))}
            </select>
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1.5 text-sm font-bold">
              {t('title')}
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
              />
            </label>
            <label className="grid gap-1.5 text-sm font-bold">
              {t('dueDate')}
              <Input
                type="date"
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
                required
              />
            </label>
          </div>
          <label className="grid gap-1.5 text-sm font-bold">
            {t('description')}
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-bold">
            {t('acceptanceCriteria')}
            <Textarea
              value={acceptanceCriteria}
              onChange={(event) => setAcceptanceCriteria(event.target.value)}
              required
            />
          </label>
          <ExecutionMemberPicker
            label={t('assignees')}
            members={members}
            value={assigneeIds}
            onChange={setAssigneeIds}
          />
          <label className="flex items-center gap-2 text-sm font-bold">
            <input
              type="checkbox"
              checked={reviewerRequired}
              onChange={(event) => setReviewerRequired(event.target.checked)}
            />
            {t('requireReviewerRecommendation')}
          </label>
          {reviewerRequired ? (
            <ExecutionMemberPicker
              label={t('reviewers')}
              members={members}
              value={reviewerIds}
              onChange={setReviewerIds}
              eligibleRoles={['advisor', 'co_advisor', 'reviewer']}
            />
          ) : null}
          <Button
            className="justify-self-start"
            type="submit"
            disabled={
              mutation.isPending ||
              !milestoneId ||
              !title.trim() ||
              !dueDate ||
              !acceptanceCriteria.trim() ||
              !assigneeIds.length ||
              (reviewerRequired && !reviewerIds.length)
            }
          >
            {t('createDeliverable')}
          </Button>
        </>
      )}
    </form>
  );
}
