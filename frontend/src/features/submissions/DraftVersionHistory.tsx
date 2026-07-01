import { FileText } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { StatusBadge } from '../../shared/ui/StatusBadge';

type Version = {
  id: number;
  versionNumber?: number;
  version_number?: number;
  reviewStatus?: string;
  review_status?: string;
};

export function DraftVersionHistory({ versions, onSelect }: { versions: Version[]; onSelect?: (version: Version) => void }) {
  return (
    <ol className="timeline" aria-label="Draft version history">
      {versions.map((version) => (
        <li key={version.id} className="items-center">
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
            <Button type="button" variant="link" className="justify-start" onClick={() => onSelect?.(version)}>
              Version {version.versionNumber ?? version.version_number}
            </Button>
          </div>
          <StatusBadge status={version.reviewStatus ?? version.review_status ?? 'pending_review'} />
        </li>
      ))}
    </ol>
  );
}
