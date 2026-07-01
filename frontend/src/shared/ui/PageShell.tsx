import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

type PageShellProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function PageShell({ title, description, actions, children, className }: PageShellProps) {
  return (
    <section className={cn('space-y-6', className)}>
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-extrabold leading-tight md:text-3xl">{title}</h1>
          {description ? <p className="mt-2 max-w-3xl text-sm text-muted-foreground md:text-base">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
