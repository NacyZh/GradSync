import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useCallback, useRef } from 'react';
import { FilePlus2, History, UploadCloud } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';
import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
import { FormStatus } from '../../shared/ui/FormStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { DraftVersionHistory } from './DraftVersionHistory';
import { createDraft, listDrafts, submitDraftVersion } from './api';

export function DraftSubmissionPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const { notify } = useAppFeedback();
  const versionFormRef = useRef<HTMLFormElement>(null);
  const draftsQuery = useQuery({ queryKey: ['drafts', projectId], queryFn: () => listDrafts(projectId), enabled: Boolean(projectId) });
  const createDraftMutation = useMutation({
    mutationFn: (title: string) => createDraft(projectId, title),
    onSuccess: () => {
      notify('Draft created', 'success');
      draftsQuery.refetch();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const submitMutation = useMutation({
    mutationFn: (payload: { draftId: number; content_reference: string; summary?: string }) =>
      submitDraftVersion(projectId, payload.draftId, { content_reference: payload.content_reference, summary: payload.summary }),
    onSuccess: () => notify('Draft version submitted', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  function onCreateDraft(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createDraftMutation.mutate(String(new FormData(event.currentTarget).get('title')));
  }

  function onSubmitVersion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    submitMutation.mutate({
      draftId: Number(form.get('draftId')),
      content_reference: String(form.get('contentReference')),
      summary: String(form.get('summary') ?? ''),
    });
  }

  const submitShortcut = useCallback(() => {
    versionFormRef.current?.requestSubmit();
  }, []);
  useSubmitShortcut(submitShortcut);

  return (
    <PageShell
      title="Submit draft"
      description="Create a draft family, submit immutable versions, and track review status in this project."
      className="submission-workspace"
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(20rem,0.85fr)_minmax(24rem,1.15fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-4 w-4" aria-hidden="true" />
              Draft library
            </CardTitle>
            <CardDescription>Families group immutable submitted versions.</CardDescription>
          </CardHeader>
          <CardContent>
          {draftsQuery.isLoading ? <DataState state="loading" message="Loading drafts" /> : null}
          {draftsQuery.data?.results.length === 0 ? <DataState state="empty" title="No draft families" message="No draft families yet." /> : null}
          <ul className="resource-list">
            {draftsQuery.data?.results.map((draft) => (
              <li key={draft.id}>
                <strong>{draft.title}</strong>
                <StatusBadge status={draft.status} />
              </li>
            ))}
          </ul>
          <h3 className="mt-5 text-sm font-extrabold">Version navigation</h3>
          <DraftVersionHistory versions={submitMutation.data ? [submitMutation.data] : []} />
          </CardContent>
        </Card>
        <section className="grid gap-4" aria-label="Student draft actions">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FilePlus2 className="h-4 w-4" aria-hidden="true" />
                Create draft family
              </CardTitle>
              <CardDescription>Use a stable family for all versions of the same paper.</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="stacked-form" aria-label="Create draft" onSubmit={onCreateDraft}>
                <FormField id="draft-title" name="title" label="Draft title" required disabled={createDraftMutation.isPending} />
                <Button type="submit" disabled={createDraftMutation.isPending}>
                  Create draft
                </Button>
                <FormStatus error={createDraftMutation.error?.message} success={createDraftMutation.isSuccess ? 'Draft created' : undefined} />
              </form>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UploadCloud className="h-4 w-4" aria-hidden="true" />
                Submit version
              </CardTitle>
              <CardDescription>Comments stay anchored to this exact version.</CardDescription>
            </CardHeader>
            <CardContent>
              <form ref={versionFormRef} className="stacked-form" aria-label="Submit draft" onSubmit={onSubmitVersion}>
                <FieldGroup>
                  <label className="grid gap-1.5 text-sm font-bold text-muted-foreground">
                    Draft
                    <select name="draftId" required disabled={submitMutation.isPending}>
                      {draftsQuery.data?.results.map((draft) => (
                        <option key={draft.id} value={draft.id}>
                          {draft.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <FormField id="draft-content-reference" name="contentReference" label="Content reference" required disabled={submitMutation.isPending} />
                  <TextareaField id="draft-summary" name="summary" label="Summary" disabled={submitMutation.isPending} />
                </FieldGroup>
                <Button type="submit" disabled={submitMutation.isPending}>
                  Submit draft
                </Button>
                <KeyboardHint>Ctrl+Enter submits</KeyboardHint>
                <FormStatus error={submitMutation.error?.message} success={submitMutation.isSuccess ? 'Draft version submitted' : undefined} />
              </form>
            </CardContent>
          </Card>
        </section>
      </div>
    </PageShell>
  );
}
