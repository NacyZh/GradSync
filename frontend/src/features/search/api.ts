import { apiRequest } from '@/shared/api/client';

export type GlobalSearchResultType =
  | 'project'
  | 'task'
  | 'report'
  | 'paper'
  | 'document'
  | 'code'
  | 'member';

export type GlobalSearchResult = {
  id: string;
  type: GlobalSearchResultType;
  title: string;
  context: string;
  path: string;
  projectId: number | null;
};

export type GlobalSearchResponse = {
  query: string;
  results: GlobalSearchResult[];
  counts: Record<GlobalSearchResultType, number>;
};

export function searchWorkspace(query: string, limit = 5) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiRequest<GlobalSearchResponse>(`/api/search/?${params.toString()}`);
}
