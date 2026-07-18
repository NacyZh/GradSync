import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, X } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/primitives/table';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { decideRoleActivation, listRoleActivations } from './api';

export function RoleActivationPage() {
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const { data = [], isLoading, error } = useQuery({
    queryKey: ['role-activations'],
    queryFn: listRoleActivations,
  });
  const mutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: 'approve' | 'reject' }) => decideRoleActivation(id, action),
    onSuccess: () => {
      notify('Activation updated', 'success');
      return queryClient.invalidateQueries({ queryKey: ['role-activations'] });
    },
    onError: (activationError) => notify(activationError.message, 'error'),
  });

  return (
    <PageShell
      title="Role activations"
      description="Approve or reject verified teacher and administrator requests."
      actions={<Badge variant="secondary">{data.filter((item) => item.status === 'pending').length} pending</Badge>}
    >
      {isLoading ? <DataState state="loading" message="Loading role activation requests." /> : null}
      {error ? <DataState state="error" title="Role activations unavailable" message={(error as { message?: string }).message ?? 'Failed'} /> : null}
      {!isLoading && data.length === 0 ? <DataState state="empty" title="No requests" message="No elevated role requests are waiting." /> : null}
      {data.length > 0 ? (
        <section className="panel">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Requested role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Controls</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((activation) => (
                <TableRow key={activation.id}>
                  <TableCell>
                    <strong>{activation.user.nickname || activation.user.name}</strong>
                    <div className="text-sm text-muted-foreground">{activation.user.email}</div>
                  </TableCell>
                  <TableCell><StatusBadge status={activation.requestedRole} /></TableCell>
                  <TableCell><StatusBadge status={activation.status} /></TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" disabled={activation.status !== 'pending' || mutation.isPending} onClick={() => mutation.mutate({ id: activation.id, action: 'approve' })}>
                        <Check className="h-4 w-4" aria-hidden="true" />
                        Approve
                      </Button>
                      <Button size="sm" variant="outline" disabled={activation.status !== 'pending' || mutation.isPending} onClick={() => mutation.mutate({ id: activation.id, action: 'reject' })}>
                        <X className="h-4 w-4" aria-hidden="true" />
                        Reject
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </section>
      ) : null}
    </PageShell>
  );
}
