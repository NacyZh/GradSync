import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { CalendarRange, UsersRound } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';

import { DataState } from '../../shared/ui/DataState';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
import { FormStatus } from '../../shared/ui/FormStatus';
import { PageShell } from '../../shared/ui/PageShell';
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
    <PageShell
      title="Create project"
      description="Start a project workspace with dates, membership, and project-scoped records."
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.65fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Project setup</CardTitle>
            <CardDescription>Advisors can refine membership and tasks after creation.</CardDescription>
          </CardHeader>
          <CardContent>
            <form aria-label="Create project" onSubmit={onSubmit} className="grid gap-4">
              <FieldGroup>
                <FormField id="project-title" name="title" label="Project title" required disabled={mutation.isPending} />
                <TextareaField id="project-description" name="description" label="Description" disabled={mutation.isPending} />
                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField id="project-starts-on" name="startsOn" label="Start date" type="date" disabled={mutation.isPending} />
                  <FormField id="project-ends-on" name="endsOn" label="End date" type="date" disabled={mutation.isPending} />
                </div>
                <FormField
                  id="project-student-ids"
                  name="studentIds"
                  label="Student IDs"
                  description="Comma separated user IDs."
                  disabled={mutation.isPending}
                />
              </FieldGroup>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? 'Creating' : 'Create'}
              </Button>
              <FormStatus error={clientError || mutation.error?.message} success={success} />
            </form>
          </CardContent>
        </Card>
        <aside className="grid gap-4" aria-label="Project setup guidance">
          <DataState
            state="success"
            title="Project-scoped by default"
            message="Tasks, reviews, bookings, notifications, and activity stay inside explicit project membership."
          />
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CalendarRange className="h-4 w-4" aria-hidden="true" />
                Dates
              </CardTitle>
              <CardDescription>End dates cannot precede start dates.</CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UsersRound className="h-4 w-4" aria-hidden="true" />
                Members
              </CardTitle>
              <CardDescription>Add reviewers or observers from the project dashboard.</CardDescription>
            </CardHeader>
          </Card>
        </aside>
      </div>
    </PageShell>
  );
}
