'use client';

import { useCallback, useEffect, useState } from 'react';
import { ExternalLink, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

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
    <section className="glass rounded-lg p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-950">Connected tools</h2>
          <p className="mt-1 text-sm text-zinc-600">Authorize GitHub, Google Sheets, and Google Drive for task delivery.</p>
        </div>
        <button type="button" onClick={() => void loadToken()} disabled={loading} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-[#e4cdb8] bg-[#fffaf6] px-3 text-xs font-medium text-[#6f5543] disabled:opacity-60">
          <RefreshCw className="h-4 w-4" />Refresh
        </button>
      </div>
      {error && <div role="alert" className="mt-4 flex flex-wrap items-center gap-3 text-sm text-red-700"><span>{error}</span><button type="button" onClick={() => void loadToken()} className="underline">Retry</button></div>}
      {loading && !embed && <p className="mt-4 text-sm text-zinc-600">Loading secure connection panel...</p>}
      {embed?.appUser?.email && <p className="mt-3 text-xs text-zinc-500">Connection workspace for {embed.appUser.email}</p>}
      {embed && <iframe title="Fastn connected tools" src={embed.iframeUrl} className="mt-4 h-[600px] w-full border-0" allow="clipboard-write" />}
      {embed && <a href={embed.iframeUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 text-xs font-medium text-emerald-800 underline"><ExternalLink className="h-3.5 w-3.5" />Open connection panel</a>}
    </section>
  );
}
