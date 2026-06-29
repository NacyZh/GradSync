import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { AsyncState } from '../../shared/ui/AsyncState';
import { FormStatus } from '../../shared/ui/FormStatus';
import { accountAction, createAccount, listAccounts } from './api';
import type { CurrentUser } from '../auth/AuthProvider';

export function AccountAdminPage() {
  const queryClient = useQueryClient();
  const [pageUrl, setPageUrl] = useState<string | undefined>(undefined);
  const [statusMsg, setStatusMsg] = useState<{ error?: string; success?: string }>({});

  const { data, isLoading, error } = useQuery({
    queryKey: ['accounts', pageUrl],
    queryFn: () => listAccounts(pageUrl),
  });

  const createMutation = useMutation({
    mutationFn: createAccount,
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      setStatusMsg({ success: `Created account for ${user.email}` });
    },
    onError: (err: { message?: string }) => {
      setStatusMsg({ error: err?.message ?? 'Failed to create account' });
    },
  });

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: 'suspend' | 'reactivate' | 'archive' }) =>
      accountAction(id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      setStatusMsg({ success: 'Account updated' });
    },
    onError: (err: { message?: string }) => {
      setStatusMsg({ error: err?.message ?? 'Action failed' });
    },
  });

  function onCreateSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatusMsg({});
    const form = new FormData(e.currentTarget);
    createMutation.mutate({
      email: String(form.get('email')),
      name: String(form.get('name')),
      global_role: String(form.get('role')) as 'advisor' | 'student',
    });
    e.currentTarget.reset();
  }

  const accounts = data?.results ?? [];

  return (
    <section>
      <h1>Account Administration</h1>

      <FormStatus error={statusMsg.error} success={statusMsg.success} />

      <section className="panel" style={{ marginBottom: 20 }}>
        <h2>Create account</h2>
        <form aria-label="Create account" onSubmit={onCreateSubmit} className="login-form">
          <label>
            Email
            <input name="email" type="email" required disabled={createMutation.isPending} />
          </label>
          <label>
            Name
            <input name="name" required disabled={createMutation.isPending} />
          </label>
          <label>
            Role
            <select name="role" required disabled={createMutation.isPending}>
              <option value="student">Student</option>
              <option value="advisor">Advisor</option>
            </select>
          </label>
          <button className="button primary" type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating…' : 'Create account'}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>All accounts</h2>
        {isLoading ? <AsyncState state="loading" message="Loading accounts" /> : null}
        {error ? <AsyncState state="error" message={(error as { message?: string }).message ?? 'Failed'} /> : null}
        {!isLoading && accounts.length === 0 ? <AsyncState state="empty" message="No accounts" /> : null}

        {accounts.length > 0 ? (
          <table className="account-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Name</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((acct) => (
                <tr key={acct.id}>
                  <td>{acct.email}</td>
                  <td>{acct.name}</td>
                  <td>{acct.global_role}</td>
                  <td>{acct.status}</td>
                  <td className="action-cell">
                    {acct.status === 'active' ? (
                      <button
                        className="button"
                        onClick={() => actionMutation.mutate({ id: acct.id, action: 'suspend' })}
                        disabled={actionMutation.isPending}
                      >
                        Suspend
                      </button>
                    ) : null}
                    {acct.status === 'suspended' ? (
                      <button
                        className="button"
                        onClick={() => actionMutation.mutate({ id: acct.id, action: 'reactivate' })}
                        disabled={actionMutation.isPending}
                      >
                        Reactivate
                      </button>
                    ) : null}
                    {acct.status !== 'archived' ? (
                      <button
                        className="button"
                        onClick={() => actionMutation.mutate({ id: acct.id, action: 'archive' })}
                        disabled={actionMutation.isPending}
                      >
                        Archive
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}

        {data ? (
          <nav aria-label="Pagination" className="pagination">
            <button
              className="button"
              disabled={!data.previous}
              onClick={() => setPageUrl(data.previous ?? undefined)}
            >
              Previous
            </button>
            <span>
              {accounts.length} of {data.count}
            </span>
            <button
              className="button"
              disabled={!data.next}
              onClick={() => setPageUrl(data.next ?? undefined)}
            >
              Next
            </button>
          </nav>
        ) : null}
      </section>
    </section>
  );
}
