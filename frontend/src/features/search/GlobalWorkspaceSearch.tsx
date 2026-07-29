import { useQuery } from '@tanstack/react-query';
import {
  ClipboardList,
  Code2,
  FileStack,
  FileText,
  FolderKanban,
  Library,
  LoaderCircle,
  Search,
  UserRound,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { useI18n, type MessageKey } from '@/shared/i18n/I18nProvider';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';

import {
  searchWorkspace,
  type GlobalSearchResult,
  type GlobalSearchResultType,
} from './api';

type WorkspaceLink = {
  to: string;
  label: string;
};

type SearchResult = {
  id: string;
  label: string;
  description: string;
  to: string;
  type: 'workspace' | GlobalSearchResultType;
};

type Props = {
  links: WorkspaceLink[];
  role: 'admin' | 'advisor' | 'student';
};

const routeKeywords: Record<string, string> = {
  '/': 'dashboard home calendar 仪表盘 首页 日历',
  '/projects': 'projects tasks reviews reports materials 项目 任务 评审 汇报 材料',
  '/resources': 'resources booking equipment 资源 预约 设备',
  '/library/papers': 'papers library pdf 论文 文献',
  '/library/code': 'code repository archive 代码 仓库 压缩包',
  '/library/documents': 'documents files 文档 文件',
  '/writing': 'writing versions feedback 写作 版本 反馈',
  '/admin/accounts': 'accounts users team 账号 用户 成员',
  '/admin/health': 'project health operations 项目 健康 运营',
  '/admin/audit': 'audit events governance 审计 事件 治理',
  '/admin/accounts?view=requests': 'teacher access requests approvals 教师 权限 申请 审批',
  '/profile': 'profile account settings 个人资料 账号 设置',
};

const typeLabels: Record<GlobalSearchResultType, MessageKey> = {
  project: 'globalSearchProject',
  task: 'globalSearchTask',
  report: 'globalSearchReport',
  paper: 'globalSearchPaper',
  document: 'globalSearchDocument',
  code: 'globalSearchCode',
  member: 'globalSearchMember',
};

const typeIcons = {
  workspace: FileStack,
  project: FolderKanban,
  task: ClipboardList,
  report: FileText,
  paper: Library,
  document: FileStack,
  code: Code2,
  member: UserRound,
};

function normalized(value: string) {
  return value.trim().toLocaleLowerCase();
}

function mapServerResult(result: GlobalSearchResult, t: (key: MessageKey) => string): SearchResult {
  return {
    id: result.id,
    label: result.title,
    description: `${t(typeLabels[result.type])} · ${result.context}`,
    to: result.path,
    type: result.type,
  };
}

export function GlobalWorkspaceSearch({ links, role }: Props) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const searchTerm = normalized(query);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedQuery(searchTerm), 250);
    return () => window.clearTimeout(timeout);
  }, [searchTerm]);

  const searchQuery = useQuery({
    queryKey: ['global-search', debouncedQuery],
    queryFn: () => searchWorkspace(debouncedQuery),
    enabled: open && debouncedQuery.length >= 2,
    staleTime: 30_000,
  });

  const results = useMemo<SearchResult[]>(() => {
    if (!searchTerm) return [];
    const searchableLinks = role === 'admin'
      ? [...links, { to: '/admin/accounts?view=requests', label: 'Teacher access requests' }]
      : links;
    const workspaceResults = searchableLinks
      .filter((link) => normalized(`${link.label} ${routeKeywords[link.to] ?? ''}`).includes(searchTerm))
      .map((link) => ({
        id: `workspace:${link.to}`,
        label: link.label,
        description: t('globalSearchWorkspace'),
        to: link.to,
        type: 'workspace' as const,
      }));
    const domainResults = debouncedQuery === searchTerm
      ? (searchQuery.data?.results ?? []).map((result) => mapServerResult(result, t))
      : [];
    return [...workspaceResults, ...domainResults];
  }, [debouncedQuery, links, role, searchQuery.data?.results, searchTerm, t]);

  useEffect(() => {
    setActiveIndex((current) => Math.min(current, Math.max(results.length - 1, 0)));
  }, [results.length]);

  function choose(result: SearchResult) {
    setQuery('');
    setOpen(false);
    navigate(result.to);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (results[activeIndex]) choose(results[activeIndex]);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((current) => Math.min(current + 1, Math.max(results.length - 1, 0)));
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    }
    if (event.key === 'Escape') {
      setOpen(false);
      event.currentTarget.blur();
    }
  }

  const waitingForSearch = searchTerm.length >= 2
    && (debouncedQuery !== searchTerm || searchQuery.isLoading || searchQuery.isFetching);
  const searchComplete = debouncedQuery === searchTerm && searchQuery.isFetched;

  return (
    <form
      className="global-search"
      role="search"
      onSubmit={onSubmit}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <span className="sr-only">{t('search')}</span>
      <div className="global-search-control">
        <Search className="global-search-icon" aria-hidden="true" />
        <Input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
            setActiveIndex(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={t('globalSearchPlaceholder')}
          aria-label={t('search')}
          role="combobox"
          aria-autocomplete="list"
          aria-controls="global-search-results"
          aria-expanded={open && Boolean(searchTerm)}
          aria-activedescendant={results[activeIndex] ? `global-search-result-${activeIndex}` : undefined}
        />
        {query ? (
          <Button type="button" variant="ghost" size="icon" className="global-search-clear" aria-label={t('globalSearchClear')} onClick={() => setQuery('')}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      {open && searchTerm ? (
        <div className="global-search-popover">
          {searchTerm.length < 2 ? <p className="global-search-state" role="status">{t('globalSearchMinimum')}</p> : null}
          {waitingForSearch ? (
            <p className="global-search-state" role="status"><LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> {t('globalSearchLoading')}</p>
          ) : null}
          {searchQuery.isError ? <p className="global-search-state text-destructive" role="status">{t('globalSearchUnavailable')}</p> : null}
          {searchComplete && results.length === 0 ? <p className="global-search-state" role="status">{t('globalSearchNoResults')}</p> : null}
          {results.length ? (
            <ul id="global-search-results" role="listbox" aria-label={t('globalSearchResults')}>
              {results.map((result, index) => {
                const Icon = typeIcons[result.type];
                return (
                  <li key={result.id}>
                    <button
                      id={`global-search-result-${index}`}
                      type="button"
                      role="option"
                      aria-selected={index === activeIndex}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => choose(result)}
                    >
                      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                      <span><strong>{result.label}</strong><small>{result.description}</small></span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      ) : null}
    </form>
  );
}
