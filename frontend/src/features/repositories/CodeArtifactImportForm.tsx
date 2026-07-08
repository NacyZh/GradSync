import { FolderOpen, X } from 'lucide-react';
import { useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { LocalizedValidation } from '../../shared/ui/LocalizedValidation';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { useCodeArtifactUpload, type CodeArtifact } from './api';

const ALLOWED_ARCHIVE_EXTENSIONS = ['.zip', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.7z'];
const ARCHIVE_ACCEPT = `${ALLOWED_ARCHIVE_EXTENSIONS.join(',')},application/zip,application/gzip,application/x-tar`;

function formatFileSize(size: number) {
  const units = [
    ['GB', 1024 ** 3],
    ['MB', 1024 ** 2],
    ['KB', 1024],
  ] as const;
  for (const [unit, factor] of units) {
    if (size >= factor) {
      return `${(size / factor).toFixed(1).replace(/\.0$/, '')} ${unit}`;
    }
  }
  return `${size} bytes`;
}

function isSupportedArchive(file: File) {
  const name = file.name.toLowerCase();
  return ALLOWED_ARCHIVE_EXTENSIONS.some((extension) => name.endsWith(extension));
}

function errorMessage(err: unknown) {
  if (err instanceof Error) return err.message;
  if (err && typeof err === 'object' && 'message' in err) return String(err.message);
  return 'Archive upload failed';
}

type CodeArtifactImportFormProps = {
  projectId: number;
  onUploaded?: (artifact: CodeArtifact) => void;
};

export function CodeArtifactImportForm({ projectId, onUploaded }: CodeArtifactImportFormProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [visibility, setVisibility] = useState<'project_members' | 'group_wide'>('project_members');
  const [archive, setArchive] = useState<File | undefined>();
  const [uploadComplete, setUploadComplete] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useCodeArtifactUpload(projectId);
  const archiveError = archive && !isSupportedArchive(archive)
    ? 'Choose a supported archive file: .zip, .tar, .gz, .tgz, .bz2, .xz, or .7z.'
    : archive && archive.size <= 0
      ? 'Choose a non-empty archive file.'
      : '';
  const visibleError = archiveError || error;

  function chooseArchive() {
    fileInputRef.current?.click();
  }

  function clearArchive(options: { keepComplete?: boolean } = {}) {
    setArchive(undefined);
    setError('');
    if (!options.keepComplete) {
      setUploadComplete(false);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const selectedArchive = archive;
    if (!selectedArchive || archiveError) return;
    setError('');
    setUploadComplete(false);
    try {
      const uploadedArtifact = await uploadMutation.mutateAsync({
        archive: selectedArchive,
        name,
        description,
        tags,
        visibility,
      });
      setUploadComplete(true);
      onUploaded?.(uploadedArtifact);
      setName('');
      setDescription('');
      setTags('');
      clearArchive({ keepComplete: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <form className="grid min-w-0 gap-3 overflow-hidden rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements
        title="Code archive upload"
        extensions={ALLOWED_ARCHIVE_EXTENSIONS}
        maxSizeLabel="100 MB"
        description={`Allowed archives: ${ALLOWED_ARCHIVE_EXTENSIONS.join(', ')} up to 100 MB`}
      />
      <div className="grid min-w-0 gap-2">
        <input
          ref={fileInputRef}
          className="hidden"
          aria-label="Archive file"
          name="archive"
          type="file"
          accept={ARCHIVE_ACCEPT}
          onChange={(event) => {
            setArchive(event.target.files?.[0]);
            setError('');
            setUploadComplete(false);
          }}
          required
        />
        <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
          <Button type="button" variant="outline" className="min-w-0" onClick={chooseArchive} aria-label={archive ? 'Reselect archive' : 'Choose archive'}>
            <FolderOpen className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">{archive ? 'Reselect archive' : 'Choose archive'}</span>
          </Button>
          {archive ? (
            <Button type="button" variant="ghost" className="min-w-0" onClick={() => clearArchive()} aria-label="Clear selected archive">
              <X className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="truncate">Clear</span>
            </Button>
          ) : null}
        </div>
        {archive ? (
          <div className="grid min-w-0 gap-1 rounded-md border bg-muted/20 p-2 text-xs text-muted-foreground" aria-label="Selected archive summary">
            <p className="min-w-0 truncate font-medium text-foreground" title={archive.name}>Selected archive: {archive.name}</p>
            <p>{formatFileSize(archive.size)}</p>
          </div>
        ) : null}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <Input aria-label="Artifact name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Artifact name" required />
        <Input aria-label="Tags" value={tags} onChange={(event) => setTags(event.target.value)} placeholder="simulation, python" />
      </div>
      <Input
        aria-label="Artifact description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder="Searchable archive description"
        required
      />
      <select
        aria-label="Code archive visibility"
        className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={visibility}
        onChange={(event) => setVisibility(event.target.value as 'project_members' | 'group_wide')}
      >
        <option value="project_members">Project members</option>
        <option value="group_wide">Group wide</option>
      </select>
      <Button type="submit" disabled={!archive || Boolean(archiveError) || uploadMutation.isPending}>Upload archive</Button>
      {uploadMutation.isPending ? <UploadProgress label="Uploading archive" value={65} /> : null}
      <LocalizedValidation message={visibleError} />
      {uploadComplete ? <p role="status" className="text-sm font-medium text-success">Upload complete</p> : null}
    </form>
  );
}
