import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, ClipboardList, Send, XCircle } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/shared/ui/primitives/button';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { DataState } from '../../shared/ui/DataState';
import { FormStatus } from '../../shared/ui/FormStatus';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import type { LaboratoryResource, ResourceUseSubmission } from './api';
import { createResourceUseSubmission, decideResourceUseSubmission, listResourceUseSubmissions } from './api';

type ResourceUseSubmissionPanelProps = {
  resources: LaboratoryResource[];
  canManage: boolean;
};

export function ResourceUseSubmissionPanel({ resources, canManage }: ResourceUseSubmissionPanelProps) {
  const queryClient = useQueryClient();
  const [resourceId, setResourceId] = useState(resources[0]?.id ? String(resources[0].id) : '');
  const [submissionType, setSubmissionType] = useState<ResourceUseSubmission['submissionType']>('request');
  const submissionsQuery = useQuery({ queryKey: ['resource-use-submissions'], queryFn: listResourceUseSubmissions });
  const submissions = useMemo(() => (submissionsQuery.data?.results ?? []).map((submission) => ({
    ...submission,
    resourceName: resources.find((resource) => resource.id === submission.resourceId)?.name ?? `Resource #${submission.resourceId}`,
  })), [resources, submissionsQuery.data]);
  const pendingSubmissions = submissions.filter((submission) => submission.status === 'pending');
  const activeResources = useMemo(
    () => resources.filter((resource) => resource.status !== 'retired'),
    [resources],
  );
  useEffect(() => {
    if (activeResources.length === 0) {
      setResourceId('');
      return;
    }
    if (!activeResources.some((resource) => String(resource.id) === resourceId)) {
      setResourceId(String(activeResources[0].id));
    }
  }, [activeResources, resourceId]);

  const createMutation = useMutation({
    mutationFn: (payload: { resourceId: number; submissionType: ResourceUseSubmission['submissionType']; details: string }) =>
      createResourceUseSubmission(payload.resourceId, {
        submissionType: payload.submissionType,
        details: payload.details,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resource-use-submissions'] }),
  });
  const decisionMutation = useMutation({
    mutationFn: (payload: { submissionId: number; status: 'confirmed' | 'rejected'; decisionNote?: string }) =>
      decideResourceUseSubmission(payload.submissionId, {
        status: payload.status,
        decisionNote: payload.decisionNote,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resource-use-submissions'] }),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    createMutation.mutate({
      resourceId: Number(form.get('resourceId')),
      submissionType,
      details: String(form.get('details') ?? ''),
    });
  }

  function decide(submissionId: number, status: 'confirmed' | 'rejected') {
    decisionMutation.mutate({
      submissionId,
      status,
      decisionNote: status === 'confirmed' ? 'Approved' : 'Rejected',
    });
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(18rem,0.9fr)_minmax(22rem,1.1fr)]">
      <form className="panel grid gap-4" aria-label="Submit resource use" onSubmit={onSubmit}>
        <div>
          <h2 className="flex items-center gap-2">
            <Send className="h-4 w-4" aria-hidden="true" />
            Resource use
          </h2>
          <p className="text-sm text-muted-foreground">Submit a request or usage record without changing inventory.</p>
        </div>
        {activeResources.length === 0 ? <DataState state="empty" title="No active resources" message="No resources are currently available for use submissions." /> : null}
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUseResource">Resource</Label>
          <Select name="resourceId" value={resourceId} onValueChange={setResourceId} disabled={activeResources.length === 0}>
            <SelectTrigger id="resourceUseResource" aria-label="Use resource">
              <SelectValue placeholder="Choose a resource" />
            </SelectTrigger>
            <SelectContent>
              {activeResources.map((resource) => (
                <SelectItem key={resource.id} value={String(resource.id)}>
                  {resource.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUseType">Submission type</Label>
          <Select value={submissionType} onValueChange={(value) => setSubmissionType(value as ResourceUseSubmission['submissionType'])}>
            <SelectTrigger id="resourceUseType" aria-label="Submission type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="request">Request</SelectItem>
              <SelectItem value="use_record">Use record</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="resourceUseDetails">Use details</Label>
          <Textarea id="resourceUseDetails" name="details" required placeholder="Purpose, expected timing, or completed-use notes" />
        </div>
        <Button type="submit" disabled={createMutation.isPending || activeResources.length === 0}>
          <Send className="h-4 w-4" aria-hidden="true" />
          Submit use request
        </Button>
        <FormStatus error={createMutation.error?.message} success={createMutation.isSuccess ? 'Use submission pending' : undefined} />
      </form>

      <section className="panel" aria-label="Resource use submissions">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4" aria-hidden="true" />
              Use submissions
            </h2>
            <p className="text-sm text-muted-foreground">Pending, confirmed, and rejected resource-use outcomes.</p>
          </div>
          <StatusBadge status={`${pendingSubmissions.length} pending`} />
        </div>
        {submissions.length === 0 ? <DataState state="empty" title="No use submissions" message="Submitted resource use requests and records appear here." /> : null}
        <ul className="resource-list">
          {submissions.map((submission) => (
            <li key={submission.id} className="items-start">
              <div className="min-w-0">
                <strong>{submission.resourceName}</strong>
                <p>{submission.details}</p>
                <p className="text-sm text-muted-foreground">{submission.studentName ?? `Student #${submission.studentId}`} · {submission.submissionType.replace('_', ' ')}</p>
                {submission.decisionNote ? <small className="text-muted-foreground">{submission.decisionNote}</small> : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <StatusBadge status={submission.status} />
                </div>
                {canManage && submission.status === 'pending' ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button type="button" size="sm" onClick={() => decide(submission.id, 'confirmed')} disabled={decisionMutation.isPending}>
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      Confirm submission
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => decide(submission.id, 'rejected')} disabled={decisionMutation.isPending}>
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      Reject submission
                    </Button>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
        <FormStatus error={decisionMutation.error?.message} success={decisionMutation.isSuccess ? 'Submission confirmed' : undefined} />
      </section>
    </div>
  );
}
