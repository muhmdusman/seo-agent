'use client';

import { useEffect, useState } from 'react';
import { getCurrentUserId, logout } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/config';
import { SiteSelector } from '@/components/site-selector';
import { LoadingSpinner } from '@/components/loading-spinner';
import { AnalysisDisplay } from '@/components/analysis-display';
import { BrandMark } from '@/components/brand-mark';
import { Button } from '@/components/ui/button';

const KNOWN_STATUSES = [
  'Getting Google credentials...',
  'Fetching Search Console...',
  'Scraping website...',
  'Thinking...',
  'Completed.',
];

export default function DashboardPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [selectedSite, setSelectedSite] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [analysis, setAnalysis] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const id = await getCurrentUserId();
      if (id === null) {
        window.location.href = '/';
        return;
      }
      setUserId(id);
    })();
  }, []);

  async function handleSiteSelect(siteUrl: string) {
    if (!userId) return;

    setSelectedSite(siteUrl);
    setAnalysis('');
    setError(null);
    setStatus('');
    setIsAnalyzing(true);

    try {
      const url = `${API_BASE_URL}/agent/weekly?user_id=${encodeURIComponent(
        userId
      )}&site_url=${encodeURIComponent(siteUrl)}`;

      const res = await fetch(url, { credentials: 'include' });

      if (!res.ok || !res.body) {
        setError('Failed to start analysis');
        setIsAnalyzing(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';

        for (const rawPart of parts) {
          const part = rawPart.trim();
          if (!part.startsWith('data:')) continue;

          const payload = part.slice('data:'.length).trim();
          try {
            const parsed = JSON.parse(payload) as { message?: string };
            const message = parsed.message;
            if (typeof message !== 'string') continue;

            if (KNOWN_STATUSES.includes(message)) {
              setStatus(message);
            } else {
              setAnalysis(message);
            }
          } catch {
            // ignore parse errors
          }
        }
      }

      setIsAnalyzing(false);
    } catch {
      setError('Analysis failed');
      setIsAnalyzing(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="glass sticky top-0 z-40 rounded-none border-x-0 border-t-0">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-6 py-3.5">
          <div className="flex items-center gap-3">
            <BrandMark className="h-9 w-9" />
            <div className="flex flex-col">
              <span className="text-sm font-semibold leading-tight text-slate-900">
                Search Console Agent
              </span>
              <span className="text-xs leading-tight text-slate-500">
                Weekly SEO analysis
              </span>
            </div>
          </div>

          <Button variant="secondary" size="sm" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-2xl font-semibold text-slate-900">
            Analyze a property
          </h1>
          <p className="text-sm leading-relaxed text-slate-600">
            Pick a verified Search Console property. We combine 30 days of
            performance data with your live page content, then rank the fixes.
          </p>
        </div>

        <SiteSelector onSiteSelect={handleSiteSelect} />

        {error && (
          <div
            role="alert"
            className="glass-strong flex items-start gap-3 rounded-xl border-red-200 p-4"
          >
            <svg
              viewBox="0 0 20 20"
              aria-hidden="true"
              fill="currentColor"
              className="mt-0.5 h-4 w-4 shrink-0 text-red-600"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm0-12a.75.75 0 0 1 .75.75v4a.75.75 0 0 1-1.5 0v-4A.75.75 0 0 1 10 6Zm0 8.25a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {isAnalyzing && <LoadingSpinner text={status || 'Analyzing...'} />}

        {analysis && (
          <AnalysisDisplay siteUrl={selectedSite} analysis={analysis} />
        )}
      </main>
    </div>
  );
}
