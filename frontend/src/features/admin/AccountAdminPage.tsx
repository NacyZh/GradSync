import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Archive, RotateCcw, Search, ShieldCheck, UserPlus, UserX } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/primitives/table';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import type { CurrentUser } from '../auth/AuthProvider';
import { accountAction, createAccount, listAccounts } from './api';

export function AccountAdminPage() {
  const queryClient = useQueryClient();
  const { confirm, notify } = useAppFeedback();
  const [pageUrl, setPageUrl] = useState<string | undefined>(undefined);
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [query, setQuery] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['accounts', pageUrl],
    queryFn: () => listAccounts(pageUrl),
  });

  const createMutation = useMutation({
    mutationFn: createAccount,
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      notify(`Created account for ${user.email}`, 'success');
    },
    onError: (err: { message?: string }) => {
      notify(err?.message ?? 'Failed to create account', 'error');
    },
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

  function onCreateSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createMutation.mutate({
      email: String(form.get('email')),
      name: String(form.get('name')),
      global_role: String(form.get('role')) as 'advisor' | 'student',
    });
    e.currentTarget.reset();
  }

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
      description="Create accounts, review role-safe access, and manage account state with audit-friendly controls."
      actions={
        <>
          <Badge variant="secondary">{activeCount} active</Badge>
          <Badge variant={suspendedCount ? 'warning' : 'muted'}>{suspendedCount} suspended</Badge>
          <Badge variant="muted">{adminCount} admins</Badge>
        </>
      }
    >
      <section className="panel">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2">
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Create account
            </h2>
            <p className="text-sm text-muted-foreground">New advisor and student accounts start active and inherit role-safe navigation.</p>
          </div>
          <StatusBadge status="admin only" />
        </div>
        <form aria-label="Create account" onSubmit={onCreateSubmit} className="grid gap-4 lg:grid-cols-[minmax(14rem,1fr)_minmax(12rem,1fr)_12rem_auto]">
          <div className="grid gap-1.5">
            <Label htmlFor="accountEmail">Email</Label>
            <Input id="accountEmail" name="email" type="email" required disabled={createMutation.isPending} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="accountName">Name</Label>
            <Input id="accountName" name="name" required disabled={createMutation.isPending} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="accountRole">Role</Label>
            <Select name="role" defaultValue="student" disabled={createMutation.isPending}>
              <SelectTrigger id="accountRole" aria-label="Role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="student">Student</SelectItem>
                <SelectItem value="advisor">Advisor</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button className="self-end" type="submit" disabled={createMutation.isPending}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            {createMutation.isPending ? 'Creating…' : 'Create account'}
          </Button>
        </form>
      </section>

      <section className="panel">
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
      </section>
    </PageShell>
  );
}
