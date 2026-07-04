import { Download, Search } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useParams } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

import { DataState } from '../../shared/ui/DataState';
import { DownloadStatus } from '../../shared/ui/DownloadStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { UploadProgress } from '../../shared/ui/UploadProgress';
import { UploadRequirements } from '../../shared/ui/UploadRequirements';
import { VisibilityBadge } from '../../shared/ui/VisibilityBadge';
import {
  downloadDocument,
  useDocumentCategories,
  useDocumentUpload,
  useDocuments,
  type DocumentCategory,
  type DocumentRecord,
} from './documentApi';

function CategoryBrowser({
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
    <div className="grid gap-2" aria-label="Document categories">
      <Button type="button" variant={selectedCategoryId ? 'outline' : 'default'} onClick={() => onSelect('')}>
        All categories
      </Button>
      {categories.map((category) => (
        <button
          key={category.id}
          type="button"
          className="rounded-md border p-3 text-left hover:bg-muted data-[selected=true]:border-primary"
          data-selected={category.id === selectedCategoryId}
          onClick={() => onSelect(category.id)}
        >
          <strong>{category.name}</strong>
          {category.description ? <span className="mt-1 block text-sm text-muted-foreground">{category.description}</span> : null}
        </button>
      ))}
    </div>
  );
}

function DocumentUploadForm({ projectId, categories }: { projectId: number; categories: DocumentCategory[] }) {
  const [file, setFile] = useState<File | undefined>();
  const [title, setTitle] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState<'project_members' | 'group_wide'>('project_members');
  const [complete, setComplete] = useState(false);
  const uploadMutation = useDocumentUpload(projectId);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || !categoryId) return;
    setComplete(false);
    await uploadMutation.mutateAsync({ file, title, categoryId, description, visibility });
    setFile(undefined);
    setTitle('');
    setCategoryId('');
    setDescription('');
    setVisibility('project_members');
    setComplete(true);
  }

  return (
    <form className="grid gap-3 rounded-md border p-3" onSubmit={onSubmit} noValidate>
      <UploadRequirements title="Categorized document upload" extensions={['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md']} maxSizeLabel="50 MB" />
      <Input
        aria-label="Document file"
        type="file"
        accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,application/pdf,text/plain,text/markdown"
        onChange={(event) => setFile(event.target.files?.[0])}
        required
      />
      <Input aria-label="Document title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Document title" required />
      <select
        aria-label="Document category"
        className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={categoryId}
        onChange={(event) => setCategoryId(event.target.value)}
        required
      >
        <option value="">Select category</option>
        {categories.map((category) => (
          <option key={category.id} value={category.id}>{category.name}</option>
        ))}
      </select>
      <Textarea aria-label="Document description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Document description" />
      <select
        aria-label="Document visibility"
        className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={visibility}
        onChange={(event) => setVisibility(event.target.value as 'project_members' | 'group_wide')}
      >
        <option value="project_members">Project members</option>
        <option value="group_wide">Group wide</option>
      </select>
      <Button type="submit" disabled={!file || !title.trim() || !categoryId || uploadMutation.isPending}>Upload document</Button>
      {uploadMutation.isPending ? <UploadProgress label="Uploading document" value={65} /> : null}
      {uploadMutation.error ? <p role="alert" className="text-sm font-medium text-destructive">{uploadMutation.error.message}</p> : null}
      {complete ? <p role="status" className="text-sm font-medium text-success">Upload complete</p> : null}
    </form>
  );
}

function DocumentDetailPanel({ document }: { document?: DocumentRecord }) {
  const [status, setStatus] = useState<{ filename: string; deliveryMode: 'direct_response' | 'signed_url' } | undefined>();
  const [error, setError] = useState<string | undefined>();

  if (!document) {
    return <p className="text-sm text-muted-foreground">Select a document to inspect details and downloads.</p>;
  }

  async function onDownload() {
    if (!document) return;
    setError(undefined);
    try {
      setStatus(await downloadDocument(document.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download unavailable');
    }
  }

  return (
    <article className="grid gap-3 rounded-md border p-4" aria-label="Document detail">
      <div>
        <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
          <h3 className="text-lg font-bold">{document.title}</h3>
          <VisibilityBadge visibility={document.visibility} />
        </div>
        <p className="text-sm text-muted-foreground">{document.categoryName ?? 'Uncategorized'}</p>
      </div>
      <dl className="grid gap-2 text-sm">
        <div><dt className="font-semibold">Description</dt><dd>{document.description || 'No description'}</dd></div>
        <div><dt className="font-semibold">Uploaded</dt><dd>{document.createdAt ? new Date(document.createdAt).toLocaleDateString() : 'Unknown'}</dd></div>
        <div><dt className="font-semibold">Checksum</dt><dd className="break-all">{document.checksumSha256 || 'Unavailable'}</dd></div>
      </dl>
      <Button type="button" onClick={onDownload}>
        <Download className="h-4 w-4" aria-hidden="true" />
        Download
      </Button>
      <DownloadStatus descriptor={status} error={error} />
    </article>
  );
}

export function DocumentLibraryPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const [query, setQuery] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [visibility, setVisibility] = useState('');
  const [selected, setSelected] = useState<DocumentRecord | undefined>();
  const categoriesQuery = useDocumentCategories();
  const categories = categoriesQuery.data ?? [];
  const documentsQuery = useDocuments(projectId, query, categoryId, visibility);
  const documents = documentsQuery.data?.results ?? [];
  const selectedDocument = documents.find((document) => document.id === selected?.id) ?? documents[0];
  const emptyTitle = categoryId ? 'No documents in category' : query ? 'No document search results' : 'No documents';

  return (
    <PageShell title="Document library" description="Browse categorized work documents, upload files, search metadata, and download permitted records.">
      <div className="grid gap-4 xl:grid-cols-[16rem_minmax(22rem,1fr)_minmax(20rem,0.8fr)]">
        <section className="panel" aria-label="Category browser">
          <CategoryBrowser categories={categories} selectedCategoryId={categoryId} onSelect={setCategoryId} />
        </section>
        <section className="panel" aria-label="Document records">
          <div className="mb-4 grid gap-3">
            <div className="grid gap-2 md:grid-cols-[minmax(16rem,1fr)_12rem]">
              <label className="block">
                <span className="sr-only">Search documents</span>
                <span className="relative block">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                  <Input className="pl-9" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title, category, description" />
                </span>
              </label>
              <select
                aria-label="Document visibility filter"
                className="min-h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={visibility}
                onChange={(event) => setVisibility(event.target.value)}
              >
                <option value="">All visibility</option>
                <option value="project_members">Project members</option>
                <option value="group_wide">Group wide</option>
              </select>
            </div>
            <DocumentUploadForm projectId={projectId} categories={categories} />
          </div>
          {categoriesQuery.isLoading || documentsQuery.isLoading ? <DataState state="loading" title="Loading documents" message="Loading document categories and records." /> : null}
          {categoriesQuery.error ? <DataState state="error" title="Categories failed" message={categoriesQuery.error.message} /> : null}
          {documentsQuery.error ? <DataState state="error" title="Document search failed" message={documentsQuery.error.message} /> : null}
          {!documentsQuery.isLoading && !documents.length ? <DataState state={categoryId || query ? 'filtered-empty' : 'empty'} title={emptyTitle} message="No documents match the current filters." /> : null}
          <ul className="grid gap-2">
            {documents.map((document) => (
              <li key={document.id}>
                <button
                  type="button"
                  aria-label={`Select document ${document.title}`}
                  className="w-full rounded-md border p-3 text-left hover:bg-muted"
                  onClick={() => setSelected(document)}
                >
                  <span className="mb-2 flex flex-wrap items-start justify-between gap-2">
                    <strong>{document.title}</strong>
                    <VisibilityBadge visibility={document.visibility} />
                  </span>
                  <span className="block text-sm text-muted-foreground">{document.categoryName ?? 'Uncategorized'} · {document.description || 'No description'}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel" aria-label="Document detail">
          <DocumentDetailPanel document={selectedDocument} />
        </section>
      </div>
    </PageShell>
  );
}
