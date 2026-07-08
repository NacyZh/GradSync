import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import type { CodeArtifact } from './api';

export function CodeArtifactVersionPanel({ artifact, variant = 'detail' }: { artifact?: CodeArtifact; variant?: 'detail' | 'download' }) {
  if (!artifact) {
    return (
      <div className="rounded-md border p-4 text-sm text-muted-foreground">
        Select a code artifact to inspect versions.
      </div>
    );
  }
  const version = artifact.latestVersion;
  const filename = version?.filename ?? artifact.sourcePathLabel;
  const checksum = artifact.checksumSha256 || version?.checksumSha256;
  const isDownload = variant === 'download';

  return (
    <article className="grid min-w-0 gap-3 rounded-md border p-4">
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
        <h3 className={`${isDownload ? 'text-base' : 'text-lg'} min-w-0 break-words font-bold leading-snug`}>
          {artifact.name}
        </h3>
        <VisibilityBadge visibility={artifact.visibility} />
      </div>
      <p className="min-w-0 break-words text-sm text-muted-foreground">{artifact.description || 'No description'}</p>
      <dl className="grid min-w-0 gap-2 text-sm">
        <div className="min-w-0">
          <dt className="font-semibold">Version</dt>
          <dd className="min-w-0 break-words">{version?.versionLabel || version?.commitReference || 'Uploaded archive'}</dd>
        </div>
        <div className="min-w-0">
          <dt className="font-semibold">File</dt>
          <dd className="min-w-0 break-words">{filename || 'No archive file'}</dd>
        </div>
        {isDownload ? null : (
          <>
            <div className="min-w-0">
              <dt className="font-semibold">Tags</dt>
              <dd className="min-w-0 break-words">{artifact.tags?.join(', ') || 'No tags'}</dd>
            </div>
            <div className="min-w-0">
              <dt className="font-semibold">Checksum</dt>
              <dd className="break-all">{checksum || 'Unavailable'}</dd>
            </div>
          </>
        )}
      </dl>
    </article>
  );
}
