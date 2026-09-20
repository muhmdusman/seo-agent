'use client';

import { useCallback, useEffect, useState } from 'react';
import { GitBranch, LogOut, RefreshCw, Save } from 'lucide-react';
import { logout } from '@/lib/auth';
import { apiClient } from '@/lib/api-client';
import type { Site, SitesResponse } from '@/lib/types';
import { BrandMark } from '@/components/brand-mark';
import { SEOWorkspaceView, type WorkspaceHeaderSummary } from '@/components/seo-workspace';
import { FastnConnections } from '@/components/fastn-connections';

export default function DashboardPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSite, setSelectedSite] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [workspaceSummary, setWorkspaceSummary] = useState<WorkspaceHeaderSummary | null>(null);
  const [githubRepoUrl, setGithubRepoUrl] = useState('');
  const [repoStatus, setRepoStatus] = useState('');
  const [repoSaving, setRepoSaving] = useState(false);
  const handleWorkspaceSummary = useCallback((summary: WorkspaceHeaderSummary | null) => setWorkspaceSummary(summary), []);

  useEffect(() => {
    if (!selectedSite) return;
    const abort = new AbortController();
    void apiClient.get<{ github_repo_url: string }>(`/seo/site-settings?site_url=${encodeURIComponent(selectedSite)}`, { signal: abort.signal })
      .then(settings => { if (!abort.signal.aborted) setGithubRepoUrl(settings.github_repo_url); })
      .catch(() => { if (!abort.signal.aborted) setGithubRepoUrl(''); });
    return () => abort.abort();
  }, [selectedSite]);

  async function saveGithubRepo() {
    if (!selectedSite) return;
    setRepoSaving(true);
    setRepoStatus('');
    try {
      await apiClient.request(`/seo/site-settings?site_url=${encodeURIComponent(selectedSite)}`, {
        method: 'PUT', body: JSON.stringify({ github_repo_url: githubRepoUrl }),
      });
      setRepoStatus('Repository saved');
    } catch (err) {
      setRepoStatus(err instanceof Error ? err.message : 'Could not save repository');
    } finally {
      setRepoSaving(false);
    }
  }

  useEffect(() => {
    const abort = new AbortController();
    void Promise.allSettled([
      apiClient.get<SitesResponse>('/search-console/sites', { signal: abort.signal }),
      apiClient.get<SitesResponse>('/seo/sites', { signal: abort.signal }),
    ]).then(([google, saved]) => {
        if (abort.signal.aborted) return;
        if (google.status === 'rejected' && saved.status === 'rejected') throw google.reason;
        const entries = [...new Map([
          ...(saved.status === 'fulfilled' ? saved.value.siteEntry ?? [] : []),
          ...(google.status === 'fulfilled' ? google.value.siteEntry ?? [] : []),
        ].filter(site => site.permissionLevel !== 'siteUnverifiedUser').map(site => [site.siteUrl, site])).values()];
        setSites(entries);
        setSelectedSite(current => entries.some(site => site.siteUrl === current) ? current : entries[0]?.siteUrl ?? '');
        setError(google.status === 'rejected' ? 'Google properties could not be refreshed. Saved properties are available.' : '');
      }).catch(err => {
        if (!abort.signal.aborted) setError(err instanceof Error ? err.message : 'Could not load properties.');
      }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [retry]);

  return (
    <div className="min-h-screen text-zinc-900 [&_h1]:tracking-normal [&_h2]:tracking-normal [&_h3]:tracking-normal [&_h4]:tracking-normal">
      <header className="sticky top-0 z-20 border-b border-[#e8d2bd] bg-[#fff7ef]/95 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <BrandMark className="h-10 max-w-[160px] shrink-0" />
          </div>
          <button onClick={() => void logout()} className="flex min-h-10 shrink-0 items-center gap-2 rounded-lg border border-[#e4cdb8] bg-[#fffaf6] px-3 text-xs font-medium text-[#6f5543] shadow-sm transition hover:border-[#d1b89f] hover:text-[#2d2118]">
            <LogOut className="h-4 w-4" />Log out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:py-8">
        <div className="glass rounded-lg p-4 sm:p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-normal text-emerald-700">Dashboard</p>
              <h1 className="mt-1 text-2xl font-semibold text-zinc-950">SEO workspace</h1>
            </div>
            <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-500 sm:w-96">
              <span>Search Console property</span>
              <select aria-label="Search Console property" value={selectedSite}
              disabled={loading || !sites.length} onChange={event => {
                setWorkspaceSummary(null);
                setRepoStatus('');
                setSelectedSite(event.target.value);
              }}
                className="glass-strong min-h-10 w-full min-w-0 rounded-lg px-3 py-2 text-sm text-zinc-800 outline-none transition focus:ring-2 focus:ring-emerald-500/40">
                {!sites.length && <option value="">{loading ? 'Loading properties...' : 'No properties available'}</option>}
                {sites.map(site => <option key={site.siteUrl} value={site.siteUrl}>{site.siteUrl}</option>)}
              </select>
            </label>
          </div>
          {workspaceSummary && <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-[#ead7c4] pt-3 text-xs text-zinc-600">
            {workspaceSummary.items.map(item => <span key={item}>{item}</span>)}
          </div>}
          <div className="mt-4 border-t border-[#ead7c4] pt-4">
            <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-500 sm:max-w-xl">
              <span className="flex items-center gap-2"><GitBranch className="h-4 w-4 text-zinc-700" />GitHub repository for code and content tasks</span>
              <div className="flex gap-2">
                <input aria-label="GitHub repository URL" value={githubRepoUrl} onChange={event => setGithubRepoUrl(event.target.value)} placeholder="https://github.com/owner/repository" className="glass-strong min-h-10 min-w-0 flex-1 rounded-lg px-3 py-2 text-sm text-zinc-800 outline-none transition focus:ring-2 focus:ring-emerald-500/40" />
                <button type="button" onClick={() => void saveGithubRepo()} disabled={repoSaving || !selectedSite} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-emerald-700 px-3 text-xs font-medium text-white disabled:opacity-60"><Save className="h-4 w-4" />Save</button>
              </div>
            </label>
            {repoStatus && <p role="status" className="mt-1 text-xs text-zinc-600">{repoStatus}</p>}
          </div>
        </div>
        {error && <div role="alert" className="glass-strong flex flex-wrap items-center gap-3 rounded-lg p-3 text-sm text-red-700">
          <span>{error}</span>
          <button onClick={() => { setLoading(true); setRetry(value => value + 1); }} className="flex items-center gap-1"><RefreshCw className="h-4 w-4" />Retry</button>
        </div>}
        <FastnConnections />
        {!loading && !error && !sites.length && <p className="glass rounded-lg px-4 py-5 text-sm text-zinc-600">Connect a verified Search Console property to begin.</p>}
        {selectedSite && <SEOWorkspaceView key={selectedSite} siteUrl={selectedSite} onSummaryChange={handleWorkspaceSummary} />}
      </main>
    </div>
  );
}
