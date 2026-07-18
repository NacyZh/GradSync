import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { CalendarRange, UsersRound, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';

import { DataState } from '../../shared/ui/DataState';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
import { FormStatus } from '../../shared/ui/FormStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { createProject, type StudentOption } from './api';
import { StudentSelector } from './StudentSelector';

export function ProjectCreatePage() {
  const navigate = useNavigate();
  const [success, setSuccess] = useState('');
  const [clientError, setClientError] = useState('');
  const [students, setStudents] = useState<StudentOption[]>([]);
  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: (project) => {
      setClientError('');
      setSuccess(`Created project ${project.title}`);
      navigate(`/projects/${project.id}`);
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
      student_ids: students.map((student) => student.id),
    });
  }

  function addStudent(student: StudentOption) {
    if (students.some((selected) => selected.id === student.id)) return;
    setStudents((current) => [...current, student]);
  }

  function removeStudent(studentId: number) {
    setStudents((current) => current.filter((student) => student.id !== studentId));
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
                <section className="grid gap-3" aria-label="Student members">
                  <StudentSelector onSelect={addStudent} selectedIds={students.map((student) => student.id)} disabled={mutation.isPending} />
                  {students.length ? (
                    <ul className="flex flex-wrap gap-2" aria-label="Selected students">
                      {students.map((student) => (
                        <li key={student.id} className="inline-flex max-w-full items-center gap-2 rounded-md border px-2 py-1 text-sm">
                          <span className="truncate">{student.label}</span>
                          <Button type="button" variant="ghost" size="icon" aria-label={`Remove ${student.nickname || student.email}`} onClick={() => removeStudent(student.id)} disabled={mutation.isPending}>
                            <X className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </section>
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
