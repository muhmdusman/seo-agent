'use client';

import { useEffect, useState } from 'react';
import { getCurrentUserId, logout } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/config';
import { SiteSelector } from '@/components/site-selector';
import { LoadingSpinner } from '@/components/loading-spinner';
import { AnalysisDisplay } from '@/components/analysis-display';
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
    <div className="min-h-screen bg-zinc-50">
      <div className="mx-auto max-w-3xl px-6 py-10 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-zinc-900">SEO Dashboard</h1>
          <Button variant="secondary" onClick={() => logout()}>
            Logout
          </Button>
        </div>

        <SiteSelector onSiteSelect={handleSiteSelect} />

        {error && <p className="text-sm text-red-500">{error}</p>}

        {isAnalyzing && (
          <LoadingSpinner text={status || 'Analyzing...'} />
        )}

        {analysis && (
          <AnalysisDisplay siteUrl={selectedSite} analysis={analysis} />
        )}
      </div>
    </div>
  );
}
