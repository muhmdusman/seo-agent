'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, LoaderCircle, Play, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { API_BASE_URL } from '@/lib/config';
import { analysisEvents } from '@/lib/seo-stream';
import { ANALYSIS_MODE_LABELS, stageLabel, type AnalysisMode, type ReportHistory, type SEOReport, type SEOTask, type SEOWorkspace } from '@/lib/seo-types';
import { AnalysisDisplay } from '@/components/analysis-display';
import { SEOTaskList } from '@/components/seo-task-list';
import { SEOReviewSummary } from '@/components/seo-review-summary';

const control = 'min-h-10 w-full min-w-0 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-800 focus:outline-emerald-600';

export function SEOWorkspaceView({ siteUrl }: { siteUrl: string }) {
  const [workspace, setWorkspace] = useState<SEOWorkspace | null>(null);
  const [history, setHistory] = useState<ReportHistory>({ reports: [], next_offset: null });
  const [selectedReport, setSelectedReport] = useState<SEOReport | null>(null);
  const [size, setSize] = useState('');
  const [type, setType] = useState('');
  const [goal, setGoal] = useState('');
  const [mode, setMode] = useState<AnalysisMode>('auto');
  const [focus, setFocus] = useState('');
  const [competitors, setCompetitors] = useState('');
  const [competitorError, setCompetitorError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const siteQuery = `site_url=${encodeURIComponent(siteUrl)}`;

  const loadWorkspace = useCallback(async (signal?: AbortSignal, restorePreferences = false) => {
    const [saved, reports] = await Promise.all([
      apiClient.get<SEOWorkspace>(`/seo/workspace?${siteQuery}`, { signal }),
      apiClient.get<ReportHistory>(`/seo/reports?${siteQuery}`, { signal }),
    ]);
    if (!mounted.current || signal?.aborted) return;
    setWorkspace(saved);
    setHistory(reports);
    setSelectedReport(saved.latest_report);
    if (restorePreferences) {
      const preferences = saved.latest_report?.preferences;
      setSize(preferences?.website_number_of_pages ?? '');
      setType(preferences?.website_type ?? '');
      setGoal(preferences?.user_goal ?? '');
      setMode(preferences?.mode ?? 'auto');
      setFocus(preferences?.focus ?? '');
      setCompetitors(preferences?.competitor_urls?.join('\n') ?? '');
    }
  }, [siteQuery]);

  useEffect(() => {
    mounted.current = true;
    const initial = new AbortController();
    const timeout = window.setTimeout(() => {
      void loadWorkspace(initial.signal, true).catch(err => {
        if (!initial.signal.aborted) setError(err instanceof Error ? err.message : 'Could not load saved work.');
      }).finally(() => {
        if (!initial.signal.aborted) setLoading(false);
      });
    }, 0);
    return () => {
      mounted.current = false;
      window.clearTimeout(timeout);
      initial.abort();
      controller.current?.abort();
    };
  }, [loadWorkspace]);

  useEffect(() => {
    if (!workspace?.running || analyzing) return;
    const poll = new AbortController();
    const interval = window.setInterval(() => {
      void loadWorkspace(poll.signal).catch(err => {
        if (!poll.signal.aborted) setError(err instanceof Error ? err.message : 'Could not refresh saved work.');
      });
    }, 5000);
    return () => { window.clearInterval(interval); poll.abort(); };
  }, [workspace?.running, analyzing, loadWorkspace]);

  async function updateTask(task: SEOTask, completed: boolean, subtaskId?: string) {
    setSaving(true);
    setError('');
    try {
      const suffix = subtaskId ? `/subtasks/${subtaskId}` : '';
      const updated = await apiClient.request<SEOTask>(`/seo/tasks/${task.id}${suffix}`, {
        method: 'PATCH', body: JSON.stringify({ completed }),
      });
      if (!mounted.current) return;
      setWorkspace(current => {
        if (!current) return current;
        const tasks = current.tasks.map(item => item.id === updated.id ? updated : item);
        const pending = tasks.filter(item => !item.completed_at).length;
        return { ...current, tasks, pending_count: pending };
      });
    } catch (err) {
      if (mounted.current) setError(err instanceof Error ? err.message : 'Task could not be saved.');
    } finally {
      if (mounted.current) setSaving(false);
    }
  }

  async function startAnalysis(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (analyzing || saving || workspace?.running || !workspace?.can_analyze) return;
    const competitorUrls = competitors.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
    const invalidUrl = competitorUrls.some(value => {
      try {
        const url = new URL(value);
        return !/^https?:\/\//i.test(value) || !['http:', 'https:'].includes(url.protocol) || !url.hostname;
      } catch { return true; }
    });
    if (competitorUrls.length > 3 || invalidUrl) {
      setCompetitorError(competitorUrls.length > 3 ? 'Enter at most 3 competitor URLs.' : 'Enter a full HTTP or HTTPS URL on each line.');
      return;
    }
    setCompetitorError('');
    setAnalyzing(true);
    setError('');
    setStatus('Starting SEO review...');
    const abort = new AbortController();
    controller.current = abort;
    try {
      const response = await fetch(`${API_BASE_URL}/agent/weekly`, {
        method: 'POST', credentials: 'include', cache: 'no-store', signal: abort.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_url: siteUrl, website_number_of_pages: size, website_type: type, user_goal: goal,
          mode, focus: focus.trim(), competitor_urls: competitorUrls,
        }),
      });
      if (response.status === 401) { window.location.assign('/'); return; }
      if (!response.ok || !response.body) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === 'string' ? body.detail : 'Could not start the review.');
      }
      let completed = false;
      for await (const message of analysisEvents(response.body)) {
        if (message.type === 'error') throw new Error(message.message);
        if (message.type === 'status') setStatus(message.message ?? 'Analyzing...');
        if (message.type === 'completed') completed = true;
      }
      if (!completed) throw new Error('The connection ended early. Checking for saved results.');
    } catch (err) {
      if (!abort.signal.aborted) setError(err instanceof Error ? err.message : 'Review failed.');
    } finally {
      if (mounted.current) {
        await loadWorkspace(abort.signal).catch(() => {
          if (!abort.signal.aborted) setError('Could not reload saved work. Refresh to check the result.');
        });
        if (mounted.current) { setAnalyzing(false); setStatus(''); }
      }
    }
  }

  async function loadOlder() {
    if (history.next_offset === null) return;
    setSaving(true);
    try {
      const older = await apiClient.get<ReportHistory>(`/seo/reports?${siteQuery}&offset=${history.next_offset}`);
      if (mounted.current) setHistory(current => ({ reports: [...current.reports, ...older.reports], next_offset: older.next_offset }));
    } catch (err) {
      if (mounted.current) setError(err instanceof Error ? err.message : 'Could not load older reports.');
    } finally { if (mounted.current) setSaving(false); }
  }

  const busy = analyzing || !!workspace?.running;
  return <div className="min-w-0 space-y-6">
    {error && <div role="alert" className="flex items-start gap-2 border-l-2 border-red-600 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span></div>}
    {loading ? <p role="status" className="py-10 text-sm text-zinc-500">Loading saved work...</p> : !workspace ?
      <button onClick={() => window.location.reload()} className="flex items-center gap-2 text-sm text-emerald-800"><RefreshCw className="h-4 w-4" />Retry</button> : <>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-zinc-200 pb-4 text-xs text-zinc-500">
        <span>{workspace.covered_stages.length} areas with findings</span>
        <span>{workspace.pending_count} open tasks</span>
        <span>{workspace.framework_complete ? '9-stage framework complete · ongoing reviews and opportunities available' : `Next framework stages: ${workspace.next_stages.map(stageLabel).join(' / ')}`}</span>
        {workspace.latest_report && <span>Last review {new Date(workspace.latest_report.created_at).toLocaleString()}</span>}
        {workspace.next_review_at && <span>Suggested next review {new Date(workspace.next_review_at).toLocaleString()}</span>}
      </div>
      <form onSubmit={startAnalysis}>
        <fieldset disabled={busy || saving} className="min-w-0 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-0 flex-1 space-y-1 text-xs text-zinc-600 sm:max-w-xs"><span>Review type</span>
            <select className={control} value={mode} onChange={event => setMode(event.target.value as AnalysisMode)}>
              <option value="auto">{ANALYSIS_MODE_LABELS.auto}</option>
              <option value="review">{ANALYSIS_MODE_LABELS.review}</option>
              <option value="growth">{ANALYSIS_MODE_LABELS.growth}</option>
            </select>
          </label>
          <button disabled={!workspace.can_analyze || busy || saving} className="flex min-h-10 items-center gap-2 rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"><Play className="h-4 w-4" />{workspace.latest_report ? 'Run SEO review' : 'Start SEO review'}</button>
        </div>
        <details open={!workspace.latest_report?.preferences?.website_number_of_pages || !workspace.latest_report?.preferences?.website_type || !workspace.latest_report?.preferences?.user_goal} className="space-y-3">
          <summary className="cursor-pointer text-xs font-medium text-zinc-600">Review settings</summary>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="min-w-0 space-y-1 text-xs text-zinc-600"><span>Website size</span>
            <select required className={control} value={size} onChange={event => setSize(event.target.value)}>
              <option value="">Select size</option>{['1-10', '11-30', '31-100', '101-300', '301+'].map(value => <option key={value} value={value}>{value} pages</option>)}
            </select>
          </label>
          <label className="min-w-0 space-y-1 text-xs text-zinc-600"><span>Website type</span>
            <select required className={control} value={type} onChange={event => setType(event.target.value)}>
              <option value="">Select type</option>{['ecommerce', 'service-based', 'content/publisher', 'saas', 'other'].map(value => <option key={value} value={value}>{value}</option>)}
              {type && !['ecommerce', 'service-based', 'content/publisher', 'saas', 'other'].includes(type) && <option value={type}>{type}</option>}
            </select>
          </label>
          <label className="min-w-0 space-y-1 text-xs text-zinc-600"><span>Primary goal</span>
            <input required maxLength={500} className={control} value={goal} onChange={event => setGoal(event.target.value)} placeholder="Increase organic traffic" />
          </label>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="min-w-0 space-y-1 text-xs text-zinc-600 sm:col-span-2"><span>Focus (optional)</span>
            <input maxLength={500} className={control} value={focus} onChange={event => setFocus(event.target.value)} />
          </label>
          <label className="min-w-0 space-y-1 text-xs text-zinc-600 sm:col-span-2"><span>Competitor URLs (optional, up to 3)</span>
            <textarea rows={3} className={`${control} resize-y`} value={competitors}
              aria-invalid={!!competitorError} aria-describedby={competitorError ? 'competitor-urls-error' : undefined}
              onChange={event => { setCompetitors(event.target.value); setCompetitorError(''); }}
              placeholder={'https://competitor.example.com\nhttps://another.example.com'} />
          </label>
        </div>
        </details>
        {competitorError && <p id="competitor-urls-error" role="alert" className="text-sm text-red-700">{competitorError}</p>}
        </fieldset>
      </form>
      {busy && <p role="status" className="flex items-center gap-2 text-sm text-emerald-800"><LoaderCircle className="h-4 w-4 animate-spin" />{status || 'Review in progress...'}</p>}
      {!workspace.latest_report && !busy && <p className="text-sm text-zinc-500">No saved review for this property.</p>}
      {workspace.latest_report && <div className="grid min-w-0 items-start gap-8 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <section className="min-w-0 space-y-5">
          <div className="flex flex-wrap items-end gap-2">
            <label className="min-w-0 flex-1 space-y-1 text-xs text-zinc-500"><span>Report history</span>
              <select aria-label="Report history" value={selectedReport?.id ?? ''} className={control}
                onChange={event => setSelectedReport(history.reports.find(report => report.id === event.target.value) ?? null)}>
                {history.reports.map((report, index) => <option key={report.id} value={report.id}>{index === 0 ? 'Latest - ' : ''}{new Date(report.created_at).toLocaleString()}</option>)}
              </select>
            </label>
            {history.next_offset !== null && <button disabled={saving} onClick={() => void loadOlder()} className="min-h-10 text-xs font-medium text-emerald-800">Older reports</button>}
          </div>
          {selectedReport && <>
            {selectedReport.stages.length > 0 && <p className="text-xs text-zinc-500">{selectedReport.stages.map(stageLabel).join(' / ')}</p>}
            <SEOReviewSummary report={selectedReport} />
            <AnalysisDisplay siteUrl={siteUrl} analysis={selectedReport.report} />
          </>}
        </section>
        <SEOTaskList tasks={workspace.tasks} disabled={saving || busy} onChange={updateTask} />
      </div>}
    </>}
  </div>;
}
