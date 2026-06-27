type Version = {
  id: number;
  versionNumber?: number;
  version_number?: number;
  reviewStatus?: string;
  review_status?: string;
};

export function DraftVersionHistory({ versions }: { versions: Version[] }) {
  return (
    <ol>
      {versions.map((version) => (
        <li key={version.id}>
          Version {version.versionNumber ?? version.version_number}: {version.reviewStatus ?? version.review_status}
        </li>
      ))}
    </ol>
  );
}
