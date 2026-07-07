import type { DownloadDescriptor } from '../api/downloads';

export function DownloadStatus({
  descriptor,
  error,
  startedLabel = 'Download started:',
}: {
  descriptor?: DownloadDescriptor;
  error?: string;
  startedLabel?: string;
}) {
  if (error) return <p role="alert" className="text-sm font-medium text-destructive">{error}</p>;
  if (!descriptor) return null;
  return (
    <p role="status" className="text-sm text-muted-foreground">
      {startedLabel} {descriptor.filename}
    </p>
  );
}
