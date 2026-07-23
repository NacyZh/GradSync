import { useQuery } from '@tanstack/react-query';
import { FileStack, FolderKanban, LoaderCircle, Search, X } from 'lucide-react';
import { useEffect, useMemo, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { listProjects } from '../projects';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';

type WorkspaceLink = {
  to: string;
  label: string;
};

type SearchResult = {
  id: string;
  label: string;
  description: string;
  to: string;
  type: 'workspace' | 'project' | 'workflow';
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
  '/admin/role-activations': 'approvals roles activation 审批 角色 激活',
  '/profile': 'profile account settings 个人资料 账号 设置',
};

function normalized(value: string) {
  return value.trim().toLocaleLowerCase();
}

export function GlobalWorkspaceSearch({ links, role }: Props) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const searchTerm = normalized(query);
  const projectsQuery = useQuery({
    queryKey: ['projects', 'global-search'],
    queryFn: listProjects,
    enabled: open && Boolean(searchTerm),
    staleTime: 30_000,
  });

  const results = useMemo<SearchResult[]>(() => {
    if (!searchTerm) return [];
    const workspaceResults = links
      .filter((link) => normalized(`${link.label} ${routeKeywords[link.to] ?? ''}`).includes(searchTerm))
      .map((link) => ({
        id: `workspace:${link.to}`,
        label: link.label,
        description: t('globalSearchWorkspace'),
        to: link.to,
        type: 'workspace' as const,
      }));
    const projectResults = (projectsQuery.data?.results ?? [])
      .filter((project) => normalized(`${project.title} ${project.description} project 项目`).includes(searchTerm))
      .map((project) => ({
        id: `project:${project.id}`,
        label: project.title,
        description: t('globalSearchProject'),
        to: `/projects/${project.id}`,
        type: 'project' as const,
      }));
    const workflows = [
      { suffix: '', label: t('globalSearchTasks'), keywords: 'task tasks dashboard 任务 计划', roles: ['admin', 'advisor', 'student'] },
      { suffix: 'materials', label: t('globalSearchMaterials'), keywords: 'material materials 材料', roles: ['admin', 'advisor', 'student'] },
      { suffix: 'reports', label: t('globalSearchReports'), keywords: 'report reports progress 汇报 进展', roles: ['admin', 'student'] },
      { suffix: 'reviews', label: t('globalSearchReviews'), keywords: 'review reviews feedback 评审 审核 反馈', roles: ['admin', 'advisor'] },
    ].filter((workflow) => workflow.roles.includes(role) && normalized(`${workflow.label} ${workflow.keywords}`).includes(searchTerm));
    const workflowResults = (projectsQuery.data?.results ?? []).flatMap((project) => workflows.map((workflow) => ({
      id: `workflow:${project.id}:${workflow.suffix || 'dashboard'}`,
      label: `${project.title} · ${workflow.label}`,
      description: t('globalSearchProjectWorkflow'),
      to: `/projects/${project.id}${workflow.suffix ? `/${workflow.suffix}` : ''}`,
      type: 'workflow' as const,
    })));
    return [...workspaceResults, ...projectResults, ...workflowResults].slice(0, 8);
  }, [links, projectsQuery.data?.results, role, searchTerm, t]);

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
      setActiveIndex((current) => Math.min(current + 1, results.length - 1));
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
          {projectsQuery.isLoading ? (
            <p className="global-search-state" role="status"><LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> {t('globalSearchLoading')}</p>
          ) : null}
          {projectsQuery.isError ? <p className="global-search-state text-destructive" role="status">{t('globalSearchUnavailable')}</p> : null}
          {!projectsQuery.isLoading && results.length === 0 ? <p className="global-search-state" role="status">{t('globalSearchNoResults')}</p> : null}
          {results.length ? (
            <ul id="global-search-results" role="listbox" aria-label={t('globalSearchResults')}>
              {results.map((result, index) => {
                const Icon = result.type === 'workspace' ? FileStack : FolderKanban;
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
