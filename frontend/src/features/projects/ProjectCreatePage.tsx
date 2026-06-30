import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { FormStatus } from '../../shared/ui/FormStatus';
import { createProject } from './api';

export function ProjectCreatePage() {
  const [success, setSuccess] = useState('');
  const [clientError, setClientError] = useState('');
  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: (project) => {
      setClientError('');
      setSuccess(`Created project ${project.title}`);
    },
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const startsOn = String(form.get('startsOn') ?? '');
    const endsOn = String(form.get('endsOn') ?? '');
    setSuccess('');
    if (startsOn && endsOn && endsOn < startsOn) {
      setClientError('Project end date cannot be before start date');
      return;
    }
    setClientError('');
    mutation.mutate({
      title: String(form.get('title') ?? ''),
      description: String(form.get('description') ?? ''),
      starts_on: startsOn || null,
      ends_on: endsOn || null,
      student_ids: String(form.get('studentIds') ?? '')
        .split(',')
        .map((value) => Number(value.trim()))
        .filter(Boolean),
    });
  }

  return (
    <section>
      <h1>Create project</h1>
      <form aria-label="Create project" onSubmit={onSubmit}>
        <label>
          Project title
          <input name="title" required />
        </label>
        <label>
          Description
          <textarea name="description" />
        </label>
        <label>
          Start date
          <input name="startsOn" type="date" />
        </label>
        <label>
          End date
          <input name="endsOn" type="date" />
        </label>
        <label>
          Student IDs
          <input name="studentIds" aria-describedby="student-id-help" />
        </label>
        <small id="student-id-help">Comma separated user IDs.</small>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Creating...' : 'Create'}
        </button>
        <FormStatus error={clientError || mutation.error?.message} success={success} />
      </form>
    </section>
  );
}
