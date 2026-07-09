import { Globe2, LockKeyhole } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';

export function VisibilityBadge({
  visibility = 'project_members',
}: {
  visibility?: 'project_members' | 'group_wide' | string;
}) {
  const groupWide = visibility === 'group_wide';
  const Icon = groupWide ? Globe2 : LockKeyhole;
  return (
    <Badge variant={groupWide ? 'secondary' : 'muted'} className="gap-1 capitalize">
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {visibility.replaceAll('_', ' ')}
    </Badge>
  );
}
