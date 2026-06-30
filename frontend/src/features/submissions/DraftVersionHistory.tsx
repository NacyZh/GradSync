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
        <li key={version.id}>
          <button type="button" className="link-button" onClick={() => onSelect?.(version)}>
            Version {version.versionNumber ?? version.version_number}: {version.reviewStatus ?? version.review_status}
          </button>
        </li>
      ))}
    </ol>
  );
}
