import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Archive, RotateCcw, Search, ShieldCheck, UserX } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/primitives/table';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import type { CurrentUser } from '../auth/AuthProvider';
import { accountAction, listAccounts, listRoleActivations } from './api';
import { RoleActivationPanel } from './RoleActivationPanel';

export function AccountAdminPage() {
  const queryClient = useQueryClient();
  const { confirm, notify } = useAppFeedback();
  const [pageUrl, setPageUrl] = useState<string | undefined>(undefined);
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedView = searchParams.get('view');
  const view = requestedView === 'requests' || requestedView === 'history' ? requestedView : 'accounts';

  const { data, isLoading, error } = useQuery({
    queryKey: ['accounts', pageUrl],
    queryFn: () => listAccounts(pageUrl),
  });
  const pendingActivationsQuery = useQuery({
    queryKey: ['role-activations', 'pending', '', undefined],
    queryFn: () => listRoleActivations({ status: 'pending' }),
  });

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: 'suspend' | 'reactivate' | 'archive' }) =>
      accountAction(id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      notify('Account updated', 'success');
    },
    onError: (err: { message?: string }) => {
      notify(err?.message ?? 'Action failed', 'error');
    },
  });

  const accounts = useMemo(() => data?.results ?? [], [data?.results]);
  const filteredAccounts = useMemo(
    () => accounts.filter((account) => {
      const searchable = `${account.email} ${account.name} ${account.global_role} ${account.status}`.toLowerCase();
      const matchesQuery = searchable.includes(query.toLowerCase());
      const matchesRole = roleFilter === 'all' || account.global_role === roleFilter;
      const matchesStatus = statusFilter === 'all' || account.status === statusFilter;
      return matchesQuery && matchesRole && matchesStatus;
    }),
    [accounts, query, roleFilter, statusFilter],
  );
  const activeCount = accounts.filter((account) => account.status === 'active').length;
  const suspendedCount = accounts.filter((account) => account.status === 'suspended').length;
  const adminCount = accounts.filter((account) => account.global_role === 'admin').length;

  async function runAccountAction(account: CurrentUser, action: 'suspend' | 'reactivate' | 'archive') {
    if (action === 'archive') {
      const ok = await confirm({
        title: 'Archive account?',
        message: `Archiving ${account.email} removes the account from active workflows. Existing project records remain auditable.`,
        actionLabel: 'Archive account',
      });
      if (!ok) return;
    }
    actionMutation.mutate({ id: account.id, action });
  }

  return (
    <PageShell
      title="Account administration"
      description="Manage account lifecycle and review verified teacher access requests."
      actions={
        <>
          <Badge variant="secondary">{activeCount} active</Badge>
          <Badge variant={suspendedCount ? 'warning' : 'muted'}>{suspendedCount} suspended</Badge>
          <Badge variant="muted">{adminCount} admins</Badge>
        </>
      }
    >
      <nav className="flex min-w-0 gap-1 overflow-x-auto border-b pb-2" aria-label="Account administration views">
        <Button variant={view === 'accounts' ? 'secondary' : 'ghost'} onClick={() => setSearchParams({ view: 'accounts' })}>
          Accounts
        </Button>
        <Button variant={view === 'requests' ? 'secondary' : 'ghost'} onClick={() => setSearchParams({ view: 'requests' })}>
          Teacher access requests
          <Badge variant={pendingActivationsQuery.data?.count ? 'warning' : 'muted'}>
            {pendingActivationsQuery.data?.count ?? 0}
          </Badge>
        </Button>
        <Button variant={view === 'history' ? 'secondary' : 'ghost'} onClick={() => setSearchParams({ view: 'history' })}>
          Decision history
        </Button>
      </nav>

      {view === 'accounts' ? <section className="panel">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              Account controls
            </h2>
            <p className="text-sm text-muted-foreground">Filter by role and status before suspending, reactivating, or archiving users.</p>
          </div>
          <Badge variant="secondary">{filteredAccounts.length} visible</Badge>
        </div>
        <div className="mb-4 grid gap-3 lg:grid-cols-[minmax(16rem,1fr)_12rem_12rem_auto]">
          <label className="grid gap-1.5 text-sm font-bold" htmlFor="accountSearch">
            Search accounts
            <span className="relative">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input id="accountSearch" className="pl-9" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, email, role" />
            </span>
          </label>
          <label className="grid gap-1.5 text-sm font-bold">
            Role
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger aria-label="Account role filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All roles</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="advisor">Advisor</SelectItem>
                <SelectItem value="student">Student</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label className="grid gap-1.5 text-sm font-bold">
            Status
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger aria-label="Account status filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <Button type="button" variant="outline" className="self-end" onClick={() => {
            setQuery('');
            setRoleFilter('all');
            setStatusFilter('all');
          }}>
            Clear
          </Button>
        </div>
        {isLoading ? <DataState state="loading" message="Loading accounts." /> : null}
        {error ? <DataState state="error" title="Accounts unavailable" message={(error as { message?: string }).message ?? 'Failed'} /> : null}
        {!isLoading && accounts.length === 0 ? <DataState state="empty" title="No accounts" message="No accounts are available." /> : null}
        {!isLoading && accounts.length > 0 && filteredAccounts.length === 0 ? (
          <DataState state="filtered-empty" title="No matching accounts" message="No accounts match the current filters." />
        ) : null}

        {filteredAccounts.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="min-w-64">Controls</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAccounts.map((acct) => (
                <TableRow key={acct.id}>
                  <TableCell className="font-bold">{acct.email}</TableCell>
                  <TableCell>{acct.name}</TableCell>
                  <TableCell><StatusBadge status={acct.global_role} /></TableCell>
                  <TableCell><StatusBadge status={acct.status} /></TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                    {acct.status === 'active' ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => runAccountAction(acct, 'suspend')}
                        disabled={actionMutation.isPending}
                      >
                        <UserX className="h-3.5 w-3.5" aria-hidden="true" />
                        Suspend
                      </Button>
                    ) : null}
                    {acct.status === 'suspended' ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => runAccountAction(acct, 'reactivate')}
                        disabled={actionMutation.isPending}
                      >
                        <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                        Reactivate
                      </Button>
                    ) : null}
                    {acct.status !== 'archived' ? (
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => runAccountAction(acct, 'archive')}
                        disabled={actionMutation.isPending}
                      >
                        <Archive className="h-3.5 w-3.5" aria-hidden="true" />
                        Archive
                      </Button>
                    ) : null}
                    {acct.status === 'archived' ? <Badge variant="muted">Read-only account</Badge> : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : null}

        {data ? (
          <nav aria-label="Pagination" className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={!data.previous}
              onClick={() => setPageUrl(data.previous ?? undefined)}
            >
              Previous
            </Button>
            <span className="text-sm font-bold text-muted-foreground">
              {accounts.length} of {data.count}
            </span>
            <Button
              type="button"
              variant="outline"
              disabled={!data.next}
              onClick={() => setPageUrl(data.next ?? undefined)}
            >
              Next
            </Button>
          </nav>
        ) : null}
      </section> : null}
      {view === 'requests' ? <RoleActivationPanel mode="pending" /> : null}
      {view === 'history' ? <RoleActivationPanel mode="processed" /> : null}
    </PageShell>
  );
}
