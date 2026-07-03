import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import type { CodeArtifact } from './api';

export function CodeArtifactVersionPanel({ artifact }: { artifact?: CodeArtifact }) {
  if (!artifact) return <p className="text-sm text-muted-foreground">Select a code artifact to inspect versions.</p>;
  const version = artifact.latestVersion;
  const filename = version?.filename ?? artifact.sourcePathLabel;
  const checksum = artifact.checksumSha256 || version?.checksumSha256;
  return (
    <article className="grid gap-3 rounded-md border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="text-lg font-bold">{artifact.name}</h3>
        <VisibilityBadge visibility={artifact.visibility} />
      </div>
      <p className="text-sm text-muted-foreground">{artifact.description || 'No description'}</p>
      <dl className="grid gap-2 text-sm">
        <div><dt className="font-semibold">Version</dt><dd>{version?.versionLabel || version?.commitReference || 'Uploaded archive'}</dd></div>
        <div><dt className="font-semibold">File</dt><dd>{filename || 'No archive file'}</dd></div>
        <div><dt className="font-semibold">Tags</dt><dd>{artifact.tags?.join(', ') || 'No tags'}</dd></div>
        <div><dt className="font-semibold">Checksum</dt><dd className="break-all">{checksum || 'Unavailable'}</dd></div>
      </dl>
    </article>
  );
}
