'use client';

import { useEffect, useState } from 'react';
import { LogOut, RefreshCw } from 'lucide-react';
import { logout } from '@/lib/auth';
import { apiClient } from '@/lib/api-client';
import type { Site, SitesResponse } from '@/lib/types';
import { BrandMark } from '@/components/brand-mark';
import { SEOWorkspaceView } from '@/components/seo-workspace';

export default function DashboardPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSite, setSelectedSite] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

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
    <div className="min-h-screen bg-white text-zinc-900 [&_h1]:tracking-normal [&_h2]:tracking-normal [&_h3]:tracking-normal [&_h4]:tracking-normal">
      <header className="border-b border-zinc-200 bg-zinc-50">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <BrandMark className="h-8 w-8 shrink-0" />
            <span className="text-sm font-semibold">Search Console Agent</span>
          </div>
          <button onClick={() => void logout()} className="flex shrink-0 items-center gap-2 text-xs text-zinc-600 hover:text-zinc-900">
            <LogOut className="h-4 w-4" />Log out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <h1 className="text-xl font-semibold">SEO workspace</h1>
          <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-500 sm:w-96">
            <span>Search Console property</span>
            <select aria-label="Search Console property" value={selectedSite}
              disabled={loading || !sites.length} onChange={event => setSelectedSite(event.target.value)}
              className="min-h-10 w-full min-w-0 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-800">
              {!sites.length && <option value="">{loading ? 'Loading properties...' : 'No properties available'}</option>}
              {sites.map(site => <option key={site.siteUrl} value={site.siteUrl}>{site.siteUrl}</option>)}
            </select>
          </label>
        </div>
        {error && <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-red-700">
          <span>{error}</span>
          <button onClick={() => { setLoading(true); setRetry(value => value + 1); }} className="flex items-center gap-1"><RefreshCw className="h-4 w-4" />Retry</button>
        </div>}
        {!loading && !error && !sites.length && <p className="text-sm text-zinc-500">No verified Search Console properties found.</p>}
        {selectedSite && <SEOWorkspaceView key={selectedSite} siteUrl={selectedSite} />}
      </main>
    </div>
  );
}
