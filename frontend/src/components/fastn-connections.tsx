'use client';

import { useCallback, useEffect, useState } from 'react';
import { Database, ExternalLink, FileText, GitBranch, Globe2, HardDrive, MessageSquare, RefreshCw, Search } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

const integrations = [
  { name: 'GitHub', icon: GitBranch, status: 'Workflow tool', tone: 'core' },
  { name: 'Google Sheets', icon: Database, status: 'Workflow tool', tone: 'core' },
  { name: 'Google Drive', icon: HardDrive, status: 'Workflow tool', tone: 'core' },
  { name: 'SerpAPI', icon: Search, status: 'Available next', tone: 'next' },
  { name: 'ButterCMS', icon: FileText, status: 'Available next', tone: 'next' },
  { name: 'WordPress.com', icon: Globe2, status: 'Available next', tone: 'next' },
  { name: 'Slack', icon: MessageSquare, status: 'Available next', tone: 'next' },
] as const;

type EmbedToken = {
  iframeUrl: string;
  expiresIn: number;
  endOrgId?: string;
  appUser?: {
    email?: string;
  };
};

export function FastnConnections() {
  const [embed, setEmbed] = useState<EmbedToken | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadToken = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const token = await apiClient.post<EmbedToken>('/fastn/embed-token');
      setEmbed(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load Fastn connections.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadToken(), 0);
    const onMessage = (event: MessageEvent) => {
      if (event.data === 'fastn:session-expired' || event.data?.type === 'fastn:session-expired') void loadToken();
    };
    window.addEventListener('message', onMessage);
    return () => {
      window.clearTimeout(initialLoad);
      window.removeEventListener('message', onMessage);
    };
  }, [loadToken]);

  return (
    <section className="glass rounded-lg p-4 sm:p-5" aria-busy={loading}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-emerald-700">Integrations</p>
          <h2 className="mt-1 text-lg font-semibold text-zinc-950">Tool connections</h2>
          <p className="mt-1 max-w-2xl text-sm text-zinc-600">Manage the tools behind SEO delivery, reporting, content workflows, and destination pickers.</p>
        </div>
        <button type="button" onClick={() => void loadToken()} disabled={loading} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-[#e4cdb8] bg-[#fffaf6] px-3 text-xs font-medium text-[#6f5543] transition hover:border-[#d1b89f] hover:text-[#2d2118] disabled:opacity-60">
          <RefreshCw className="h-4 w-4" />Refresh
        </button>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7" aria-label="Available integrations">
        {integrations.map(({ name, icon: Icon, status, tone }) => (
          <div key={name} className="min-w-0 rounded-lg border border-[#ead7c4] bg-[#fffaf6] p-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${tone === 'core' ? 'bg-emerald-100 text-emerald-800' : 'bg-[#f4e7d9] text-[#7d5b43]'}`}>
                <Icon className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="truncate text-xs font-semibold text-zinc-900">{name}</span>
            </div>
            <p className={`mt-2 text-[11px] ${tone === 'core' ? 'text-emerald-800' : 'text-[#80634f]'}`}>{status}</p>
          </div>
        ))}
      </div>
      {error && <div role="alert" className="mt-4 flex flex-wrap items-center gap-3 text-sm text-red-700"><span>{error}</span><button type="button" onClick={() => void loadToken()} className="underline">Retry</button></div>}
      {loading && !embed && <p className="mt-4 text-sm text-zinc-600">Loading secure connection panel...</p>}
      {embed?.appUser?.email && <p className="mt-3 text-xs text-zinc-500">Connection workspace for {embed.appUser.email}</p>}
      {embed && <div className="mt-5 border-t border-[#ead7c4] pt-5">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-zinc-950">Connection manager</h3>
            <p className="mt-1 text-xs text-zinc-600">Use the secure Fastn panel to connect or review tools for this workspace.</p>
          </div>
          <span className="text-[11px] font-medium uppercase tracking-normal text-zinc-500">7 tools available</span>
        </div>
        <iframe title="Fastn tool connection manager" src={embed.iframeUrl} className="mt-4 h-[600px] w-full border-0" allow="clipboard-write" />
      </div>}
      {embed && <a href={embed.iframeUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 text-xs font-medium text-emerald-800 underline"><ExternalLink className="h-3.5 w-3.5" />Open connection panel</a>}
    </section>
  );
}
