import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useCallback, useRef } from 'react';

import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FormStatus } from '../../shared/ui/FormStatus';
import { AsyncState } from '../../shared/ui/AsyncState';
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
    <section className="submission-workspace">
      <div className="page-heading">
        <div>
          <h1>Submit draft</h1>
          <p>Create a draft family, submit immutable versions, and track review status in this project.</p>
        </div>
      </div>
      <div className="two-column-workspace">
        <section className="panel">
          <h2>Draft library</h2>
          {draftsQuery.isLoading ? <AsyncState state="loading" message="Loading drafts" /> : null}
          {draftsQuery.data?.results.length === 0 ? <AsyncState state="empty" message="No draft families yet." /> : null}
          <ul className="resource-list">
            {draftsQuery.data?.results.map((draft) => (
              <li key={draft.id}>
                <strong>{draft.title}</strong>
                <span className={`status-pill ${draft.status}`}>{draft.status}</span>
              </li>
            ))}
          </ul>
          <DraftVersionHistory versions={submitMutation.data ? [submitMutation.data] : []} />
        </section>
        <section className="panel">
          <h2>Student actions</h2>
          <form className="stacked-form" aria-label="Create draft" onSubmit={onCreateDraft}>
            <label>
              Draft title
              <input name="title" required />
            </label>
            <button type="submit">Create draft</button>
            <FormStatus error={createDraftMutation.error?.message} success={createDraftMutation.isSuccess ? 'Draft created' : undefined} />
          </form>
          <form ref={versionFormRef} className="stacked-form" aria-label="Submit draft" onSubmit={onSubmitVersion}>
            <label>
              Draft
              <select name="draftId" required>
                {draftsQuery.data?.results.map((draft) => (
                  <option key={draft.id} value={draft.id}>
                    {draft.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Content reference
              <input name="contentReference" required />
            </label>
            <label>
              Summary
              <textarea name="summary" />
            </label>
            <button type="submit">Submit draft</button>
            <KeyboardHint>Ctrl+Enter submits</KeyboardHint>
            <FormStatus error={submitMutation.error?.message} success={submitMutation.isSuccess ? 'Draft version submitted' : undefined} />
          </form>
        </section>
      </div>
    </section>
  );
}
