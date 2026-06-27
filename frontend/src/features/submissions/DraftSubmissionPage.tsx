import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { FormStatus } from '../../shared/ui/FormStatus';
import { createDraft, listDrafts, submitDraftVersion } from './api';

export function DraftSubmissionPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const draftsQuery = useQuery({ queryKey: ['drafts', projectId], queryFn: () => listDrafts(projectId), enabled: Boolean(projectId) });
  const createDraftMutation = useMutation({ mutationFn: (title: string) => createDraft(projectId, title), onSuccess: () => draftsQuery.refetch() });
  const submitMutation = useMutation({
    mutationFn: (payload: { draftId: number; content_reference: string; summary?: string }) =>
      submitDraftVersion(projectId, payload.draftId, { content_reference: payload.content_reference, summary: payload.summary }),
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

  return (
    <section>
      <h1>Submit draft</h1>
      <form aria-label="Create draft" onSubmit={onCreateDraft}>
        <label>
          Draft title
          <input name="title" required />
        </label>
        <button type="submit">Create draft</button>
        <FormStatus error={createDraftMutation.error?.message} success={createDraftMutation.isSuccess ? 'Draft created' : undefined} />
      </form>
      <form aria-label="Submit draft" onSubmit={onSubmitVersion}>
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
        <FormStatus error={submitMutation.error?.message} success={submitMutation.isSuccess ? 'Draft version submitted' : undefined} />
      </form>
    </section>
  );
}
