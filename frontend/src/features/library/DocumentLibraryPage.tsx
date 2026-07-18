import { Download, FolderOpen, Pencil, Search, Trash2, X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { useParams } from 'react-router-dom';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';

import { DataState } from '../../shared/ui/DataState';
import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import { useAuth } from '../auth/AuthProvider';
import {
  downloadDocument,
  downloadSharedDocument,
  useDeleteDocument,
  useDocumentCategories,
  useDocumentUpload,
  useDocuments,
  useRenameDocument,
  useSharedDocumentUpload,
  useSharedDocuments,
  type DocumentCategory,
  type DocumentRecord,
} from './documentApi';

const EMPTY_CATEGORIES: DocumentCategory[] = [];

function formatBytes(size: number) {
  if (size < 1024) return `${size} bytes`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function getErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'message' in err) {
    return String(err.message);
  }
  return fallback;
}

function capability(document: DocumentRecord | undefined, name: 'canDownload' | 'canRename' | 'canDelete') {
  if (!document) return false;
  if (!document.actionCapabilities) {
    return name === 'canDownload' && document.status === 'active' && Boolean(document.documentFileId);
  }
  return Boolean(document.actionCapabilities[name]);
}

function CategorySelector({
  categories,
  selectedCategoryId,
  onSelect,
}: {
  categories: DocumentCategory[];
  selectedCategoryId: string;
  onSelect: (categoryId: string) => void;
}) {
  if (!categories.length) {
    return <DataState state="empty" title="No categories" message="Create document categories before uploading documents." />;
  }

  return (
    <div className="grid min-w-0 gap-2" aria-label="Document categories">
      <div className="flex min-w-0 flex-wrap gap-2">
        {categories.map((category) => (
          <button
            key={category.id}
            type="button"
            aria-label={`Category ${category.name}`}
            aria-pressed={category.id === selectedCategoryId}
            data-selected={category.id === selectedCategoryId ? 'true' : 'false'}
            className={`min-h-10 max-w-full min-w-0 rounded-md border px-3 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
              category.id === selectedCategoryId
                ? 'border-primary bg-primary/10 text-foreground'
                : 'bg-background hover:bg-muted'
            }`}
            onClick={() => onSelect(category.id)}
          >
            <span className="block truncate font-medium">{category.name}</span>
          </button>
        ))}
      </div>
      <p className="min-w-0 break-words text-xs text-muted-foreground">
        Selected category filters the list and sets the upload destination.
      </p>
    </div>
  );
}

function DocumentUploadForm({
  projectId,
  selectedCategory,
  onUploaded,
  canUploadGroupWide,
  standalone = false,
}: {
  projectId: number;
  selectedCategory?: DocumentCategory;
  onUploaded: (document: DocumentRecord) => void;
  canUploadGroupWide: boolean;
  standalone?: boolean;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | undefined>();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState<'project_members' | 'group_wide'>('project_members');
  const [uploadError, setUploadError] = useState('');
  const { notify } = useAppFeedback();
  const uploadMutation = useDocumentUpload(projectId);
  const sharedUploadMutation = useSharedDocumentUpload();
  const activeUploadMutation = standalone ? sharedUploadMutation : uploadMutation;

  function clearFile() {
    setFile(undefined);
    setUploadError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || !selectedCategory) return;
    setUploadError('');
    try {
      const uploaded = await activeUploadMutation.mutateAsync({
        file,
        title,
        categoryId: selectedCategory.id,
        description,
        visibility: !standalone && canUploadGroupWide && visibility === 'group_wide' ? 'group_wide' : undefined,
      });
      onUploaded(uploaded);
      setFile(undefined);
      setTitle('');
      setDescription('');
      setVisibility('project_members');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      notify('Upload complete', 'success');
    } catch (err) {
      const message = getErrorMessage(err, 'Document upload failed');
      setUploadError(message);
      notify(message, 'error');
    }
  }

  return (
    <form className="grid min-w-0 gap-3 overflow-hidden rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements
        title="Categorized document upload"
        extensions={['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md']}
        maxSizeLabel="50 MB"
      />
      <input
        ref={fileInputRef}
        className="hidden"
        aria-label="Document file"
        type="file"
        accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,application/pdf,text/plain,text/markdown"
        onChange={(event) => {
          setFile(event.target.files?.[0]);
          setUploadError('');
        }}
      />
      <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
        <Button
          type="button"
          variant="outline"
          className="min-w-0"
          onClick={() => {
            if (fileInputRef.current) fileInputRef.current.value = '';
            fileInputRef.current?.click();
          }}
          aria-label={file ? 'Reselect file' : 'Choose file'}
        >
          <FolderOpen className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span className="truncate">{file ? 'Reselect file' : 'Choose file'}</span>
        </Button>
        {file ? (
          <Button
            type="button"
            variant="ghost"
            className="min-w-0"
            onClick={clearFile}
            aria-label="Clear selected file"
          >
            <X className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">Clear</span>
          </Button>
        ) : null}
      </div>
      {file ? (
        <p role="status" className="min-w-0 break-words rounded-md border bg-muted/20 p-2 text-xs text-muted-foreground">
          Selected document: {file.name} · {formatBytes(file.size)}
        </p>
      ) : null}
      <p className="min-w-0 break-words text-xs text-muted-foreground">
        Destination: {selectedCategory?.name ?? 'Select a category'}
      </p>
      <Input aria-label="Document title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Optional title" />
      <Textarea aria-label="Document description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Optional description" />
      {!standalone && canUploadGroupWide ? (
        <select
          aria-label="Document visibility"
          className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={visibility}
          onChange={(event) => setVisibility(event.target.value as 'project_members' | 'group_wide')}
        >
          <option value="project_members">Project members</option>
          <option value="group_wide">Group wide</option>
        </select>
      ) : null}
      <Button type="submit" disabled={!file || !selectedCategory || activeUploadMutation.isPending}>Upload document</Button>
      {activeUploadMutation.isPending ? <UploadProgress label="Uploading document" value={65} /> : null}
      <LocalizedUploadError message={uploadError} />
    </form>
  );
}

function LocalizedUploadError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="min-w-0 break-words text-sm font-medium text-destructive">{message}</p>;
}

function SelectedDownloadPanel({ document, standalone = false }: { document?: DocumentRecord; standalone?: boolean }) {
  const [status, setStatus] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    setStatus(undefined);
    setError(undefined);
  }, [document?.id]);

  async function onDownload() {
    if (!document) return;
    setError(undefined);
    try {
      setStatus(await (standalone ? downloadSharedDocument(document.id, document.title) : downloadDocument(document.id, document.title)));
    } catch (err) {
      setError(getErrorMessage(err, 'Download unavailable'));
    }
  }

  if (!document) {
    return (
      <section className="grid min-w-0 gap-3 rounded-md border p-3" aria-label="Selected document download">
        <h2 className="text-sm font-semibold">No document selected</h2>
        <p className="text-sm text-muted-foreground">Select a document from the list to enable download.</p>
        <Button type="button" disabled>
          <Download className="h-4 w-4" aria-hidden="true" />
          Download
        </Button>
      </section>
    );
  }

  const canDownload = capability(document, 'canDownload');

  return (
    <section className="grid min-w-0 gap-3 rounded-md border p-3" aria-label="Selected document download">
      <div className="grid min-w-0 gap-1">
        <h2 className="line-clamp-2 min-w-0 break-words text-sm font-semibold">{document.title}</h2>
        <p className="truncate text-xs text-muted-foreground">{document.categoryName ?? 'Uncategorized'}</p>
      </div>
      <Button type="button" onClick={onDownload} disabled={!canDownload} aria-label={`Download ${document.title}`}>
        <Download className="h-4 w-4" aria-hidden="true" />
        Download
      </Button>
      <DownloadStatus descriptor={status} error={error} />
    </section>
  );
}

function DocumentDetailPanel({
  document,
  onRename,
  onDelete,
}: {
  document?: DocumentRecord;
  onRename: (newTitle: string) => Promise<DocumentRecord>;
  onDelete: () => Promise<void>;
}) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameTitle, setRenameTitle] = useState('');
  const [renameError, setRenameError] = useState<string | undefined>();
  const [isSavingRename, setIsSavingRename] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | undefined>();
  const [isDeleting, setIsDeleting] = useState(false);

  if (!document) {
    return <DataState state="empty" title="No document selected" message="Select a document to inspect details." />;
  }

  const canRename = capability(document, 'canRename');
  const canDelete = capability(document, 'canDelete');

  function startRename() {
    if (!document) return;
    setRenameTitle(document.title);
    setRenameError(undefined);
    setIsConfirmingDelete(false);
    setIsRenaming(true);
  }

  async function submitRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanedTitle = renameTitle.trim();
    if (!cleanedTitle) {
      setRenameError('Document title is required');
      return;
    }
    setRenameError(undefined);
    setIsSavingRename(true);
    try {
      await onRename(cleanedTitle);
      setIsRenaming(false);
    } catch (err) {
      setRenameError(getErrorMessage(err, 'Rename unavailable'));
    } finally {
      setIsSavingRename(false);
    }
  }

  function startDelete() {
    setDeleteError(undefined);
    setIsRenaming(false);
    setIsConfirmingDelete(true);
  }

  async function submitDelete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDeleteError(undefined);
    setIsDeleting(true);
    try {
      await onDelete();
      setIsConfirmingDelete(false);
    } catch (err) {
      setDeleteError(getErrorMessage(err, 'Delete unavailable'));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <article className="grid min-w-0 gap-3 rounded-md border p-4" aria-label="Document detail">
      <div className="min-w-0">
        <div className="mb-2 flex min-w-0 flex-wrap items-start justify-between gap-2">
          <h3 className="line-clamp-3 min-w-0 break-words text-lg font-bold">{document.title}</h3>
          <VisibilityBadge visibility={document.visibility} />
        </div>
        <p className="min-w-0 truncate text-sm text-muted-foreground">{document.categoryName ?? 'Uncategorized'}</p>
      </div>
      <dl className="grid min-w-0 gap-2 text-sm">
        <div className="min-w-0">
          <dt className="font-semibold">Description</dt>
          <dd className="min-w-0 break-words">{document.description || 'No description'}</dd>
        </div>
        <div>
          <dt className="font-semibold">Uploaded</dt>
          <dd>{document.createdAt ? new Date(document.createdAt).toLocaleDateString() : 'Unknown'}</dd>
        </div>
        <div className="min-w-0">
          <dt className="font-semibold">Checksum</dt>
          <dd className="min-w-0 break-all">{document.checksumSha256 || 'Unavailable'}</dd>
        </div>
      </dl>
      <div className="flex min-w-0 flex-wrap gap-2">
        {canRename ? (
          <Button type="button" variant="outline" size="sm" onClick={startRename} aria-label="Rename document">
            <Pencil className="h-4 w-4" aria-hidden="true" />
            Rename
          </Button>
        ) : null}
        {canDelete ? (
          <Button type="button" variant="outline" size="sm" onClick={startDelete} aria-label="Delete document">
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Delete
          </Button>
        ) : null}
      </div>
      {isRenaming ? (
        <form onSubmit={submitRename} className="grid min-w-0 gap-2 rounded-md border p-3">
          <label className="grid min-w-0 gap-1 text-sm font-semibold">
            New document title
            <input
              aria-label="New document title"
              className="min-h-10 min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm font-normal"
              value={renameTitle}
              maxLength={255}
              onChange={(event) => setRenameTitle(event.target.value)}
            />
          </label>
          {renameError ? <p role="alert" className="min-w-0 break-words text-sm text-destructive">{renameError}</p> : null}
          <div className="flex min-w-0 flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isSavingRename}>Save title</Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsRenaming(false)}>Cancel</Button>
          </div>
        </form>
      ) : null}
      {isConfirmingDelete ? (
        <form onSubmit={submitDelete} className="grid min-w-0 gap-2 rounded-md border border-destructive/40 p-3">
          <div className="grid min-w-0 gap-1 text-sm">
            <p className="min-w-0 break-words font-semibold text-destructive">Delete {document.title}</p>
            <p className="text-muted-foreground">This archives the selected document and removes it from ordinary search and download.</p>
          </div>
          {deleteError ? <p role="alert" className="min-w-0 break-words text-sm text-destructive">{deleteError}</p> : null}
          <div className="flex min-w-0 flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isDeleting}>Confirm delete</Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setIsConfirmingDelete(false)}>Cancel</Button>
          </div>
        </form>
      ) : null}
    </article>
  );
}

export function DocumentLibraryPage() {
  const { user } = useAuth();
  const projectIdParam = useParams().projectId;
  const projectId = Number(projectIdParam ?? 0);
  const standalone = !projectIdParam;
  const [query, setQuery] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [uploadedDocuments, setUploadedDocuments] = useState<Record<string, DocumentRecord>>({});
  const [renamedDocuments, setRenamedDocuments] = useState<Record<string, DocumentRecord>>({});
  const [deletedDocumentIds, setDeletedDocumentIds] = useState<Set<string>>(() => new Set());
  const categoriesQuery = useDocumentCategories();
  const categories = categoriesQuery.data ?? EMPTY_CATEGORIES;
  const selectedCategory = categories.find((category) => category.id === categoryId);
  const projectDocumentsQuery = useDocuments(projectId, query, categoryId, '');
  const sharedDocumentsQuery = useSharedDocuments(query, categoryId, standalone);
  const documentsQuery = standalone ? sharedDocumentsQuery : projectDocumentsQuery;
  const renameMutation = useRenameDocument(projectId);
  const deleteMutation = useDeleteDocument(projectId);
  const documents = useMemo(() => {
    const byId = new Map<string, DocumentRecord>();
    for (const document of documentsQuery.data?.results ?? []) {
      byId.set(document.id, document);
    }
    for (const document of Object.values(uploadedDocuments)) {
      if (!categoryId || document.categoryId === categoryId) {
        byId.set(document.id, document);
      }
    }
    for (const document of Object.values(renamedDocuments)) {
      if (!categoryId || document.categoryId === categoryId) {
        byId.set(document.id, document);
      }
    }
    return Array.from(byId.values()).filter((document) => !deletedDocumentIds.has(document.id));
  }, [categoryId, deletedDocumentIds, documentsQuery.data, renamedDocuments, uploadedDocuments]);
  const canUploadGroupWide = Boolean(
    user?.global_role === 'advisor'
      || user?.global_role === 'admin'
      || documents.some((document) => document.actionCapabilities?.canUploadGroupWide),
  );
  const selectedDocument = documents.find((document) => document.id === selectedId);
  const displayDocument = selectedDocument ?? (!selectedId ? documents[0] : undefined);
  const selectedDocumentForDisplay = standalone && displayDocument
    ? {
        ...displayDocument,
        actionCapabilities: {
          canView: displayDocument.actionCapabilities?.canView ?? displayDocument.status === 'active',
          canDownload: displayDocument.actionCapabilities?.canDownload ?? Boolean(displayDocument.documentFileId),
          canRename: false,
          canDelete: false,
          canUploadGroupWide: false,
        },
      }
    : displayDocument;
  const emptyTitle = standalone
    ? query
      ? 'No document search results'
      : 'No documents'
    : categoryId
      ? 'No documents in category'
      : query
        ? 'No document search results'
        : 'No documents';

  function selectDocument(document: DocumentRecord) {
    setSelectedId(document.id);
  }

  function handleDocumentRowKeyDown(event: KeyboardEvent<HTMLButtonElement>, document: DocumentRecord) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectDocument(document);
    }
  }

  function handleUploadedDocument(document: DocumentRecord) {
    setUploadedDocuments((current) => ({ ...current, [document.id]: document }));
    setSelectedId(document.id);
  }

  async function renameSelectedDocument(newTitle: string) {
    if (!selectedDocument) {
      throw new Error('Select a document before renaming');
    }
    const renamed = await renameMutation.mutateAsync({
      documentId: selectedDocument.id,
      payload: { newTitle },
    });
    setRenamedDocuments((current) => ({ ...current, [renamed.id]: renamed }));
    return renamed;
  }

  async function deleteSelectedDocument() {
    if (!selectedDocument) {
      throw new Error('Select a document before deleting');
    }
    const deletedId = selectedDocument.id;
    await deleteMutation.mutateAsync(deletedId);
    setDeletedDocumentIds((current) => {
      const next = new Set(current);
      next.add(deletedId);
      return next;
    });
    setRenamedDocuments((current) => {
      const next = { ...current };
      delete next[deletedId];
      return next;
    });
    setUploadedDocuments((current) => {
      const next = { ...current };
      delete next[deletedId];
      return next;
    });
    setSelectedId(undefined);
  }

  useEffect(() => {
    if (!categoryId && categories.length) {
      setCategoryId(categories[0].id);
    }
  }, [categories, categoryId]);

  useEffect(() => {
    if (!documents.length) {
      setSelectedId(undefined);
      return;
    }
    if (!selectedId || !documents.some((document) => document.id === selectedId)) {
      setSelectedId(documents[0].id);
    }
  }, [documents, selectedId]);

  return (
    <PageShell
      title={standalone ? 'Shared documents' : 'Document library'}
      description={
        standalone
          ? 'Browse, upload, search, and download group shared documents.'
          : 'Browse categorized work documents, upload files, search metadata, and download permitted records.'
      }
    >
      <div
        data-testid="document-library-workspace"
        className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(16rem,0.68fr)_minmax(0,1.32fr)]"
      >
        <section className="panel relative z-10 grid min-w-0 content-start gap-4" aria-label="Document library upload and download region">
          <DocumentUploadForm
            projectId={projectId}
            selectedCategory={selectedCategory}
            onUploaded={handleUploadedDocument}
            canUploadGroupWide={canUploadGroupWide}
            standalone={standalone}
          />
          <SelectedDownloadPanel document={selectedDocumentForDisplay} standalone={standalone} />
        </section>
        <section className="panel relative z-10 grid min-w-0 content-start gap-4" aria-label="Document library search and display region">
          <CategorySelector categories={categories} selectedCategoryId={categoryId} onSelect={setCategoryId} />
          <label className="block min-w-0">
            <span className="sr-only">Search documents</span>
            <span className="relative block min-w-0">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input className="pl-9" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title, category, description" />
            </span>
          </label>
          {categoriesQuery.isLoading || documentsQuery.isLoading ? (
            <div data-testid="document-layout-state" className="min-w-0">
              <DataState state="loading" title="Loading documents" message="Loading document categories and records." />
            </div>
          ) : null}
          {categoriesQuery.error ? (
            <div data-testid="document-layout-state" className="min-w-0">
              <DataState state="error" title="Categories failed" message={categoriesQuery.error.message} />
            </div>
          ) : null}
          {documentsQuery.error ? (
            <div data-testid="document-layout-state" className="min-w-0">
              <DataState state="error" title="Document search failed" message={documentsQuery.error.message} />
            </div>
          ) : null}
          {!documentsQuery.isLoading && !documentsQuery.error && !documents.length ? (
            <div data-testid="document-layout-state" className="min-w-0">
              <DataState state={categoryId || query ? 'filtered-empty' : 'empty'} title={emptyTitle} message="No documents match the current filters." />
            </div>
          ) : null}
          <div className="grid min-w-0 gap-4 overflow-hidden">
            <div data-testid="document-selected-detail-region" className="min-w-0">
              <DocumentDetailPanel
                document={selectedDocumentForDisplay}
                onRename={renameSelectedDocument}
                onDelete={deleteSelectedDocument}
              />
            </div>
            <ul
              data-testid="document-results-list"
              className="grid max-h-[32rem] min-w-0 content-start gap-2 overflow-y-auto overflow-x-hidden pr-1"
              aria-label="Document search results"
            >
              {documents.map((document) => (
                <li key={document.id} className="min-w-0">
                  <button
                    type="button"
                    aria-label={`Select document ${document.title}`}
                    aria-pressed={selectedDocument?.id === document.id}
                    data-selected={selectedDocument?.id === document.id ? 'true' : 'false'}
                    data-testid="document-result-row"
                    className={`grid min-h-16 w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 overflow-hidden rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                      selectedDocument?.id === document.id
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'bg-background hover:bg-muted'
                    }`}
                    onClick={() => selectDocument(document)}
                    onKeyDown={(event) => handleDocumentRowKeyDown(event, document)}
                  >
                    <span className="grid min-w-0 gap-1">
                      <strong className="line-clamp-2 min-w-0 break-words text-sm leading-snug">{document.title}</strong>
                      <span className="block min-w-0 truncate text-xs text-muted-foreground">
                        {document.categoryName ?? 'Uncategorized'} · {document.description || 'No description'}
                      </span>
                    </span>
                    <span className="max-w-[9rem] shrink-0">
                      <VisibilityBadge visibility={document.visibility} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </PageShell>
  );
}
