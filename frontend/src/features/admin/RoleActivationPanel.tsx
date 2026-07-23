import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Search, ShieldOff, X } from 'lucide-react';
import { useState } from 'react';

import { formatUiDate } from '@/shared/i18n/translate';
import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/primitives/dialog';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/primitives/table';
import { Textarea } from '@/shared/ui/primitives/textarea';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import {
  decideRoleActivation,
  listRoleActivations,
  type RoleActivation,
} from './api';

export function RoleActivationPanel({
  mode,
}: {
  mode: 'pending' | 'processed';
}) {
  const queryClient = useQueryClient();
  const { confirm, notify } = useAppFeedback();
  const [query, setQuery] = useState('');
  const [pageUrl, setPageUrl] = useState<string>();
  const [reasonDecision, setReasonDecision] = useState<{
    activation: RoleActivation;
    action: 'reject' | 'revoke';
  } | null>(null);
  const [decisionReason, setDecisionReason] = useState('');
  const activationsQuery = useQuery({
    queryKey: ['role-activations', mode, query, pageUrl],
    queryFn: () => listRoleActivations({ status: mode, query, pageUrl }),
  });
  const mutation = useMutation({
    mutationFn: ({
      activation,
      action,
      reason = '',
    }: {
      activation: RoleActivation;
      action: 'approve' | 'reject' | 'revoke';
      reason?: string;
    }) => decideRoleActivation(activation.id, action, reason),
    onSuccess: () => {
      setReasonDecision(null);
      setDecisionReason('');
      queryClient.invalidateQueries({ queryKey: ['role-activations'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      notify('Teacher access request updated', 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const activations = activationsQuery.data?.results ?? [];

  async function approve(activation: RoleActivation) {
    const approved = await confirm({
      title: 'Approve teacher access?',
      message: `This grants ${activation.user.email} teacher workspace and project-management permissions.`,
      actionLabel: 'Approve request',
    });
    if (approved) mutation.mutate({ activation, action: 'approve' });
  }

  function submitReasonDecision() {
    const reason = decisionReason.trim();
    if (!reasonDecision || !reason) {
      notify('Decision reason is required', 'error');
      return;
    }
    mutation.mutate({
      activation: reasonDecision.activation,
      action: reasonDecision.action,
      reason,
    });
  }

  return (
    <section className="panel" aria-label={mode === 'pending' ? 'Teacher access requests' : 'Access request history'}>
      <div className="mb-4 flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2>{mode === 'pending' ? 'Teacher access requests' : 'Access request history'}</h2>
          <p className="text-sm text-muted-foreground">
            {mode === 'pending'
              ? 'Review email-verified teachers before granting elevated workspace permissions.'
              : 'Review completed teacher access decisions and their recorded reasons.'}
          </p>
        </div>
        <Badge variant={activationsQuery.data?.count ? 'warning' : 'muted'}>
          {activationsQuery.data?.count ?? 0} {mode === 'pending' ? 'pending' : 'processed'}
        </Badge>
      </div>

      <label className="mb-4 grid max-w-lg gap-1.5 text-sm font-bold">
        Search requests
        <span className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <Input
            className="pl-9"
            value={query}
            placeholder="Name, nickname, or email"
            onChange={(event) => {
              setQuery(event.target.value);
              setPageUrl(undefined);
            }}
          />
        </span>
      </label>

      {activationsQuery.isLoading ? <DataState state="loading" message="Loading teacher access requests." /> : null}
      {activationsQuery.error ? (
        <DataState state="error" title="Teacher access requests unavailable" message={activationsQuery.error.message} />
      ) : null}
      {!activationsQuery.isLoading && !activationsQuery.error && !activations.length ? (
        <DataState
          state={query ? 'filtered-empty' : 'empty'}
          title={mode === 'pending' ? 'No pending requests' : 'No processed requests'}
          message={query ? 'No teacher access requests match this search.' : 'No teacher access requests are available in this view.'}
        />
      ) : null}

      {activations.length ? (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Applicant</TableHead>
                <TableHead>Requested role</TableHead>
                <TableHead>Submitted</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>{mode === 'pending' ? 'Controls' : 'Decision'}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {activations.map((activation) => (
                <TableRow key={activation.id}>
                  <TableCell>
                    <strong>{activation.user.nickname || activation.user.name}</strong>
                    <div className="text-sm text-muted-foreground">{activation.user.email}</div>
                    <div className="text-xs text-muted-foreground">Email verified</div>
                  </TableCell>
                  <TableCell><StatusBadge status={activation.requestedRole} /></TableCell>
                  <TableCell>{formatUiDate(activation.createdAt, { year: 'numeric', month: 'short', day: 'numeric' })}</TableCell>
                  <TableCell><StatusBadge status={activation.status} /></TableCell>
                  <TableCell>
                    {mode === 'pending' ? (
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" disabled={mutation.isPending} onClick={() => approve(activation)}>
                          <Check className="h-4 w-4" aria-hidden="true" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={mutation.isPending}
                          onClick={() => setReasonDecision({ activation, action: 'reject' })}
                        >
                          <X className="h-4 w-4" aria-hidden="true" />
                          Reject
                        </Button>
                      </div>
                    ) : (
                      <div className="max-w-72 text-sm">
                        <div>{activation.reviewer?.name || 'System'} · {activation.reviewedAt ? formatUiDate(activation.reviewedAt, { year: 'numeric', month: 'short', day: 'numeric' }) : 'Not recorded'}</div>
                        {activation.reviewReason ? <p className="mt-1 break-words text-muted-foreground">{activation.reviewReason}</p> : null}
                        {activation.status === 'approved' ? (
                          <Button
                            className="mt-2"
                            size="sm"
                            variant="outline"
                            disabled={mutation.isPending}
                            onClick={() => setReasonDecision({ activation, action: 'revoke' })}
                          >
                            <ShieldOff className="h-4 w-4" aria-hidden="true" />
                            Revoke access
                          </Button>
                        ) : null}
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {activationsQuery.data ? (
        <nav aria-label="Access request pagination" className="mt-4 flex items-center justify-between gap-3">
          <Button variant="outline" disabled={!activationsQuery.data.previous} onClick={() => setPageUrl(activationsQuery.data?.previous ?? undefined)}>
            Previous
          </Button>
          <span className="text-sm font-bold text-muted-foreground">{activations.length} of {activationsQuery.data.count}</span>
          <Button variant="outline" disabled={!activationsQuery.data.next} onClick={() => setPageUrl(activationsQuery.data?.next ?? undefined)}>
            Next
          </Button>
        </nav>
      ) : null}

      <Dialog open={Boolean(reasonDecision)} onOpenChange={(open) => {
        if (!open) {
          setReasonDecision(null);
          setDecisionReason('');
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {reasonDecision?.action === 'revoke' ? 'Revoke teacher access?' : 'Reject teacher access?'}
            </DialogTitle>
            <DialogDescription>
              {reasonDecision?.action === 'revoke'
                ? 'This immediately removes teacher workspace permissions and requires a new approval before access can be restored.'
                : 'The applicant can update their registration details and submit another request.'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-1.5">
            <Label htmlFor="teacher-access-decision-reason">Decision reason</Label>
            <Textarea
              id="teacher-access-decision-reason"
              value={decisionReason}
              maxLength={1000}
              placeholder={
                reasonDecision?.action === 'revoke'
                  ? 'Record why teacher access must be removed'
                  : 'Explain what must be corrected before resubmission'
              }
              onChange={(event) => setDecisionReason(event.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReasonDecision(null)}>Cancel</Button>
            <Button variant="destructive" disabled={mutation.isPending} onClick={submitReasonDecision}>
              {reasonDecision?.action === 'revoke' ? 'Revoke access' : 'Reject request'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
