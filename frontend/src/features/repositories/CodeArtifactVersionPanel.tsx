import type { CodeArtifact } from './api';

export function CodeArtifactVersionPanel({ artifact }: { artifact?: CodeArtifact }) {
  if (!artifact) return <p className="text-sm text-muted-foreground">Select a code artifact to inspect versions.</p>;
  const version = artifact.latestVersion;
  return (
    <article className="grid gap-3 rounded-md border p-4">
      <h3 className="text-lg font-bold">{artifact.name}</h3>
      <p className="text-sm text-muted-foreground">{artifact.description || 'No description'}</p>
      {version ? (
        <dl className="grid gap-2 text-sm">
          <div><dt className="font-semibold">Version</dt><dd>{version.versionLabel || version.commitReference || 'Unlabeled'}</dd></div>
          <div><dt className="font-semibold">File</dt><dd>{version.filename}</dd></div>
          <div><dt className="font-semibold">Checksum</dt><dd className="break-all">{version.checksumSha256}</dd></div>
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">No uploaded versions yet.</p>
      )}
    </article>
  );
}
