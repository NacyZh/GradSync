import { StatusBadge } from './StatusBadge';

export function SourceProjectBadge({ title }: { title?: string }) {
  if (!title) return null;
  return <StatusBadge status={`Source: ${title}`} />;
}

export function VisibilityStateBadge({ visibility }: { visibility: 'project-only' | 'group-wide' | string }) {
  return <StatusBadge status={visibility === 'group-wide' ? 'Group-wide' : 'Project-only'} />;
}
