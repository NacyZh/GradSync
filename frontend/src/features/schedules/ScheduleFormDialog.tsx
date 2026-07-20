import { useEffect, useState, type FormEvent } from 'react';

import type { ApiError } from '../../shared/api/client';
import { ConfirmDialog } from '../../shared/ui/ConfirmDialog';
import { FormField, TextareaField } from '../../shared/ui/FormField';
import { Button } from '../../shared/ui/primitives/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../shared/ui/primitives/dialog';
import { Label } from '../../shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../shared/ui/primitives/select';
import type { AudienceOption, ScheduleDetail, ScheduleWrite } from './api';
import { ScheduleRecipientSelector } from './ScheduleRecipientSelector';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: 'student' | 'advisor' | 'admin';
  initial?: ScheduleDetail | null;
  onSubmit: (payload: ScheduleWrite) => Promise<void>;
};

const weekdays = [
  { value: 1, label: 'Monday' }, { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' }, { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' }, { value: 6, label: 'Saturday' },
  { value: 7, label: 'Sunday' },
];

function localDateTime(date: Date) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function defaultState(initial?: ScheduleDetail | null) {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 1);
  const end = new Date(start);
  end.setHours(end.getHours() + 1);
  return {
    scope: initial?.scope === 'group' ? 'group' as const : 'personal' as const,
    category: initial?.category ?? 'personal',
    title: initial?.title ?? '',
    description: initial?.description ?? '',
    allDay: initial?.allDay ?? false,
    startsAt: initial?.startsAt ? localDateTime(new Date(initial.startsAt)) : localDateTime(start),
    endsAt: initial?.endsAt ? localDateTime(new Date(initial.endsAt)) : localDateTime(end),
    startsOn: initial?.startsOn ?? new Date().toISOString().slice(0, 10),
    endsOn: initial?.endsOn ?? new Date(Date.now() + 86_400_000).toISOString().slice(0, 10),
    timezone: initial?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC',
    frequency: initial?.recurrence.frequency ?? 'none',
    interval: initial?.recurrence.interval ?? 1,
    until: initial?.recurrence.until ?? '',
    selectedWeekdays: initial?.recurrence.weekdays ?? [],
    reminders: initial?.reminders.map((item) => item.offsetMinutes) ?? [30],
    projects: (initial?.audience.projectIds ?? []).map((id) => ({ id, type: 'project' as const, label: `Project ${id}`, secondaryLabel: '', status: 'active', eligible: true, eligibilityScope: 'active_account' as const })) as AudienceOption[],
    accounts: (initial?.audience.accountIds ?? []).map((id) => ({ id, type: 'account' as const, label: `Member ${id}`, secondaryLabel: '', status: 'active', eligible: true, eligibilityScope: 'active_account' as const })) as AudienceOption[],
  };
}

export function ScheduleFormDialog({ open, onOpenChange, role, initial, onSubmit }: Props) {
  const [form, setForm] = useState(() => defaultState(initial));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [pendingConflict, setPendingConflict] = useState<ScheduleWrite | null>(null);
  const [pendingPublication, setPendingPublication] = useState<ScheduleWrite | null>(null);

  useEffect(() => {
    if (open) {
      setForm(defaultState(initial));
      setErrors({});
    }
  }, [initial, open]);

  function buildPayload(confirmConflicts = false): ScheduleWrite {
    return {
      scope: form.scope,
      category: form.category,
      title: form.title.trim(),
      description: form.description.trim(),
      allDay: form.allDay,
      startsAt: form.allDay ? null : new Date(form.startsAt).toISOString(),
      endsAt: form.allDay ? null : new Date(form.endsAt).toISOString(),
      startsOn: form.allDay ? form.startsOn : null,
      endsOn: form.allDay ? form.endsOn : null,
      timezone: form.timezone,
      recurrence: {
        frequency: form.frequency as ScheduleWrite['recurrence']['frequency'],
        interval: form.interval,
        weekdays: form.frequency === 'weekly' ? form.selectedWeekdays : [],
        until: form.frequency === 'none' ? null : form.until,
      },
      reminders: form.reminders.map((offsetMinutes) => ({ offsetMinutes })),
      audience: form.scope === 'group' ? {
        projectIds: form.projects.map((option) => option.id),
        accountIds: form.accounts.map((option) => option.id),
      } : undefined,
      confirmConflicts,
    };
  }

  async function submit(nextPayload: ScheduleWrite) {
    setSubmitting(true);
    setErrors({});
    try {
      await onSubmit(nextPayload);
    } catch (error) {
      const apiError = error as ApiError;
      if (apiError.code === 'schedule_conflict_confirmation_required') {
        setPendingConflict(nextPayload);
      } else if (apiError.fields) {
        setErrors(Object.fromEntries(Object.entries(apiError.fields).map(([key, value]) => [key, value.join(' ')])));
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form.title.trim()) {
      setErrors({ title: 'Title is required.' });
      return;
    }
    const nextPayload = buildPayload();
    if (nextPayload.scope === 'group') {
      if (!nextPayload.audience?.projectIds.length && !nextPayload.audience?.accountIds.length) {
        setErrors({ audience: 'Select at least one project or member.' });
        return;
      }
      setPendingPublication(nextPayload);
      return;
    }
    void submit(nextPayload);
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[calc(100vh-2rem)] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{initial ? 'Edit schedule' : 'New schedule'}</DialogTitle>
            <DialogDescription>Plan time without leaving the dashboard.</DialogDescription>
          </DialogHeader>
          <form className="schedule-form" onSubmit={handleSubmit}>
            {role !== 'student' ? (
              <div className="grid gap-1.5">
                <Label htmlFor="schedule-scope">Visibility</Label>
                <Select value={form.scope} onValueChange={(value: 'personal' | 'group') => setForm((current) => ({ ...current, scope: value }))}>
                  <SelectTrigger id="schedule-scope" aria-label="Visibility"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="personal">Personal</SelectItem><SelectItem value="group">Group</SelectItem></SelectContent>
                </Select>
              </div>
            ) : null}
            <FormField autoFocus id="schedule-title" label="Title" value={form.title} error={errors.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
            <TextareaField id="schedule-description" label="Description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
            <div className="grid gap-1.5">
              <Label htmlFor="schedule-category">Category</Label>
              <Select value={form.category} onValueChange={(category) => setForm((current) => ({ ...current, category }))}>
                <SelectTrigger id="schedule-category" aria-label="Category"><SelectValue /></SelectTrigger>
                <SelectContent>{['personal', 'meeting', 'seminar', 'milestone', 'defense', 'deadline', 'other'].map((value) => <SelectItem key={value} value={value}>{value.charAt(0).toUpperCase() + value.slice(1)}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <label className="schedule-check"><input type="checkbox" checked={form.allDay} onChange={(event) => setForm((current) => ({ ...current, allDay: event.target.checked }))} /> All day</label>
            <div className="grid gap-3 sm:grid-cols-2">
              {form.allDay ? (
                <><FormField id="schedule-start-date" label="Start date" type="date" value={form.startsOn} onChange={(event) => setForm((current) => ({ ...current, startsOn: event.target.value }))} /><FormField id="schedule-end-date" label="End date" type="date" value={form.endsOn} onChange={(event) => setForm((current) => ({ ...current, endsOn: event.target.value }))} /></>
              ) : (
                <><FormField id="schedule-start-time" label="Start time" type="datetime-local" value={form.startsAt} onChange={(event) => setForm((current) => ({ ...current, startsAt: event.target.value }))} /><FormField id="schedule-end-time" label="End time" type="datetime-local" value={form.endsAt} onChange={(event) => setForm((current) => ({ ...current, endsAt: event.target.value }))} /></>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="grid gap-1.5"><Label htmlFor="schedule-repeats">Repeats</Label><select id="schedule-repeats" className="schedule-native-select" value={form.frequency} onChange={(event) => setForm((current) => ({ ...current, frequency: event.target.value as ScheduleWrite['recurrence']['frequency'] }))}><option value="none">Does not repeat</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></div>
              {form.frequency !== 'none' ? <FormField id="schedule-until" label="Repeat until" type="date" value={form.until} onChange={(event) => setForm((current) => ({ ...current, until: event.target.value }))} /> : null}
            </div>
            {form.frequency === 'weekly' ? <fieldset className="schedule-weekdays"><legend>Repeat on</legend>{weekdays.map((day) => <label key={day.value}><input type="checkbox" checked={form.selectedWeekdays.includes(day.value)} onChange={() => setForm((current) => ({ ...current, selectedWeekdays: current.selectedWeekdays.includes(day.value) ? current.selectedWeekdays.filter((value) => value !== day.value) : [...current.selectedWeekdays, day.value] }))} />{day.label}</label>)}</fieldset> : null}
            {form.scope === 'group' && role !== 'student' ? (
              <fieldset className="schedule-audience-fieldset">
                <legend>Audience</legend>
                <ScheduleRecipientSelector type="project" selected={form.projects} onChange={(projects: AudienceOption[]) => setForm((current) => ({ ...current, projects }))} />
                <ScheduleRecipientSelector type="account" selected={form.accounts} onChange={(accounts: AudienceOption[]) => setForm((current) => ({ ...current, accounts }))} />
                <p>Project audiences follow active membership for future occurrences.</p>
                {errors.audience ? <p className="font-bold text-destructive" role="alert">{errors.audience}</p> : null}
              </fieldset>
            ) : null}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Saving' : initial ? 'Save changes' : form.scope === 'group' ? 'Publish schedule' : 'Create schedule'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={Boolean(pendingConflict)} title="Schedule overlaps existing work" message="The overlap is allowed. Confirm that you still want to save this schedule." actionLabel="Save anyway" destructive={false} onCancel={() => setPendingConflict(null)} onConfirm={() => { const next = pendingConflict; setPendingConflict(null); if (next) void submit({ ...next, confirmConflicts: true }); }} />
      <ConfirmDialog open={Boolean(pendingPublication)} title="Publish group schedule" message={`Publish to ${pendingPublication?.audience?.projectIds.length ?? 0} projects and ${pendingPublication?.audience?.accountIds.length ?? 0} selected members?`} actionLabel="Publish schedule" destructive={false} onCancel={() => setPendingPublication(null)} onConfirm={() => { const next = pendingPublication; setPendingPublication(null); if (next) void submit(next); }} />
    </>
  );
}
