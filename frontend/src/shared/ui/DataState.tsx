import type { ReactNode } from 'react';
import { AlertCircle, CheckCircle2, Inbox, Loader2 } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

type DataStateProps = {
  state: 'loading' | 'empty' | 'filtered-empty' | 'error' | 'success' | 'warning';
  title?: string;
  message: string;
  action?: ReactNode;
  className?: string;
};

export function DataState({ state, title, message, action, className }: DataStateProps) {
  if (state === 'loading') {
    return (
      <section className={cn('rounded-lg border border-dashed p-4', className)} role="status">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          {title ?? 'Loading'}
        </div>
        <div className="grid gap-2" aria-hidden="true">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-10/12" />
          <Skeleton className="h-4 w-8/12" />
        </div>
        <p className="mt-3 text-sm text-muted-foreground">{message}</p>
      </section>
    );
  }

  const icon = state === 'success' ? CheckCircle2 : state === 'error' ? AlertCircle : Inbox;
  const Icon = icon;
  const variant = state === 'error' ? 'destructive' : state === 'success' ? 'success' : state === 'warning' ? 'warning' : 'default';

  return (
    <Alert className={className} variant={variant} role={state === 'error' ? 'alert' : 'status'}>
      <Icon className="mr-2 inline h-4 w-4" aria-hidden="true" />
      {title ? <AlertTitle className="inline">{title}</AlertTitle> : null}
      <AlertDescription className="mt-2">
        {message}
        {action ? <div className="mt-3">{action}</div> : null}
      </AlertDescription>
    </Alert>
  );
}

export function EmptyAction({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <Button type="button" variant="outline" onClick={onClick}>
      {children}
    </Button>
  );
}
