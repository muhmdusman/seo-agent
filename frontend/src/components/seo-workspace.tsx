'use client';

import { type CSSProperties, useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Gauge, LoaderCircle, Play, RefreshCw, Server, Sparkles } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { API_BASE_URL } from '@/lib/config';
import { analysisEvents } from '@/lib/seo-stream';
import {
  ANALYSIS_MODE_LABELS,
  stageLabel,
  type AnalysisMode,
  type AuditSnapshot,
  type PageSpeedStrategySnapshot,
  type ReportHistory,
  type SEOReport,
  type SEOTask,
  type SEOWorkspace,
} from '@/lib/seo-types';
import { AnalysisDisplay } from '@/components/analysis-display';
import { SEOTaskList } from '@/components/seo-task-list';
import { SEOReviewSummary } from '@/components/seo-review-summary';

const control = 'glass-strong min-h-10 w-full min-w-0 rounded-lg px-3 py-2 text-sm text-zinc-800 outline-none transition focus:ring-2 focus:ring-emerald-500/40 disabled:cursor-not-allowed disabled:opacity-60';

function buildFocusPayload(userFocus: string) {
  return userFocus.trim().slice(0, 500);
}

function scoreColor(score: number | null | undefined) {
  if (score === null || score === undefined) return '#a1a1aa';
  if (score >= 90) return '#10b981';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}

function scoreStyle(score: number | null | undefined): CSSProperties {
  const value = Math.max(0, Math.min(score ?? 0, 100));
  return {
    background: `conic-gradient(${scoreColor(score)} ${value * 3.6}deg, #e7e2dc 0deg)`,
  };
}

function scoreItems(snapshot: PageSpeedStrategySnapshot | undefined) {
  const scores = snapshot?.scores ?? {};
  return [
    { label: 'Performance', score: scores.performance },
    { label: 'Accessibility', score: scores.accessibility },
    { label: 'Best practices', score: scores.best_practices },
    { label: 'SEO', score: scores.seo },
  ];
}

function metricItems(snapshot: PageSpeedStrategySnapshot | undefined) {
  const field = snapshot?.field ?? {};
  const lab = snapshot?.lab ?? {};
  return [
    { label: 'LCP', value: field.lcp?.display_value ?? lab.lcp?.display_value ?? 'n/a' },
    { label: 'INP', value: field.inp?.display_value ?? 'n/a' },
    { label: 'CLS', value: field.cls?.display_value ?? lab.cls?.display_value ?? 'n/a' },
    { label: 'FCP', value: field.fcp?.display_value ?? lab.fcp?.display_value ?? 'n/a' },
    { label: 'TBT', value: lab.tbt?.display_value ?? 'n/a' },
    { label: 'Speed Index', value: lab.speed_index?.display_value ?? 'n/a' },
  ];
}

function headerItems(snapshot: AuditSnapshot | null) {
  const headers = snapshot?.http_headers?.headers ?? {};
  const entries = [
    ['Status', [snapshot?.http_headers?.http_version, snapshot?.http_headers?.status_code].filter(Boolean).join(' ')],
    ['Final URL', snapshot?.http_headers?.final_url],
    ['Content type', headers['content-type']],
    ['Cache', headers['cache-control'] || headers['cf-cache-status'] || headers['x-cache'] || headers['x-vercel-cache']],
    ['Robots', headers['x-robots-tag']],
    ['HSTS', headers['strict-transport-security']],
  ];
  return entries.filter((item): item is [string, string] => Boolean(item[1]));
}

const PAGE_SPEED_STRATEGIES = ['mobile', 'desktop'];

export interface WorkspaceHeaderSummary {
  items: string[];
}

interface SEOWorkspaceViewProps {
  siteUrl: string;
  onSummaryChange?: (summary: WorkspaceHeaderSummary | null) => void;
}

function workspaceHeaderSummary(workspace: SEOWorkspace): WorkspaceHeaderSummary {
  return {
    items: [
      `${workspace.covered_stages.length} areas with findings`,
      `${workspace.pending_count} open tasks`,
      workspace.framework_complete ? '9-stage framework complete · ongoing reviews and opportunities available' : `Next framework stages: ${workspace.next_stages.map(stageLabel).join(' / ')}`,
      ...(workspace.latest_report ? [`Last review ${new Date(workspace.latest_report.created_at).toLocaleString()}`] : []),
      ...(workspace.next_review_at ? [`Suggested next review ${new Date(workspace.next_review_at).toLocaleString()}`] : []),
    ],
  };
}

function AuditSnapshotPanel({
  snapshot,
  loading,
  error,
  selectedStrategy,
  onStrategyChange,
  onRetry,
}: {
  snapshot: AuditSnapshot | null;
  loading: boolean;
  error: string;
  selectedStrategy: string;
  onStrategyChange: (strategy: string) => void;
  onRetry: () => void;
}) {
  const strategies = snapshot?.core_web_vitals?.strategies ?? {};
  const errors = snapshot?.core_web_vitals?.errors ?? {};
  const strategy = strategies[selectedStrategy];
  const selectedStrategyError = errors[selectedStrategy];
  const ready = !loading && !!snapshot;
  const unavailable = !loading && !snapshot;
  const opportunities = strategy?.opportunities ?? [];
  const headers = headerItems(snapshot);
  return (
    <section className="glass min-w-0 rounded-lg p-3 sm:p-4">
      <div className="flex flex-col gap-3 border-b border-[#ead7c4] pb-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">
            {ready ? <Sparkles className="h-4 w-4" /> : unavailable ? <AlertCircle className="h-4 w-4" /> : <LoaderCircle className="h-4 w-4 animate-spin" />}
            {ready ? 'Live audit snapshot' : unavailable ? 'Audit snapshot unavailable' : 'Loading audit snapshot'}
          </p>
          <h2 className="mt-1 break-words text-base font-semibold text-zinc-950">{snapshot?.url ?? 'Preparing property audit'}</h2>
          <p className="mt-1 text-xs text-zinc-600">
            {ready ? 'Core Web Vitals and response headers are ready for this review request.' : 'Collecting Core Web Vitals and response details for this property.'}
          </p>
          {error && <div role="alert" className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
            <p className="font-medium">We could not load the live audit data. Check your network, then refresh the audit.</p>
            <p className="mt-1 break-words text-red-700">{error}</p>
          </div>}
        </div>
        <button type="button" onClick={onRetry} disabled={loading} className={`inline-flex w-fit items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium shadow-sm disabled:opacity-60 ${unavailable ? 'border-red-200 bg-red-50 text-red-800' : 'border-emerald-100 bg-emerald-50/90 text-emerald-800'}`}>
          {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : ready ? <RefreshCw className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {ready ? 'Refresh audit data' : loading ? 'Refreshing audit...' : 'Try audit again'}
        </button>
      </div>

      {!ready ? <div className="grid min-h-52 place-items-center pt-4">
        <div role="status" className="flex flex-col items-center gap-3 text-center">
          {loading ? <LoaderCircle className="h-8 w-8 animate-spin text-emerald-700" /> : <AlertCircle className="h-8 w-8 text-red-700" />}
          <p className="text-sm font-medium text-zinc-800">{loading ? 'Preparing Core Web Vitals snapshot...' : 'Audit snapshot could not be loaded.'}</p>
          <p className="max-w-sm text-xs text-zinc-500">{loading ? 'Performance scores, Core Web Vitals, opportunities, and headers will appear here in a moment.' : 'If the network or PageSpeed API failed, click “Try audit again”. You can still run the SEO review.'}</p>
        </div>
      </div> : <div className="grid gap-3 pt-4 xl:grid-cols-[0.72fr_1fr]">
        <div className="min-w-0 space-y-3">
          <div className="inline-flex rounded-lg bg-[#f3e3d4] p-1 text-xs font-medium text-zinc-700">
            {PAGE_SPEED_STRATEGIES.map(value => (
              <button key={value} type="button" onClick={() => onStrategyChange(value)}
                className={`rounded-md px-3 py-1.5 capitalize ${selectedStrategy === value ? 'bg-emerald-700 text-white' : 'hover:bg-white'}`}>
                {value}{!strategies[value] && errors[value] ? ' issue' : ''}
              </button>
            ))}
          </div>
          {!strategy && <div role="status" className="rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2 text-xs text-amber-900">
            {selectedStrategyError ? 'Network issue. Please refresh the audit.' : `${selectedStrategy} PageSpeed data is not available yet.`}
          </div>}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-2">
            {scoreItems(strategy).map(item => (
              <div key={item.label} className="glass-strong flex min-h-24 flex-col items-center justify-center rounded-lg p-2 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full p-1" style={scoreStyle(item.score)}>
                  <div className="flex h-full w-full items-center justify-center rounded-full bg-[#fffaf6] text-base font-semibold text-zinc-900">
                    {item.score ?? 'n/a'}
                  </div>
                </div>
                <p className="mt-1.5 text-xs font-medium text-zinc-700">{item.label}</p>
              </div>
            ))}
          </div>

          <div className="glass-strong rounded-lg p-3">
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900"><Gauge className="h-4 w-4 text-emerald-700" />Core Web Vitals</p>
            <dl className="grid gap-1.5">
              {metricItems(strategy).map(metric => (
                <div key={metric.label} className="flex items-center justify-between gap-3 rounded-lg border border-[#ead7c4] bg-[#fffaf6] px-3 py-1.5">
                  <dt className="text-xs text-zinc-600">{metric.label}</dt>
                  <dd className="text-sm font-semibold text-zinc-950">{metric.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>

        <div className="grid min-w-0 gap-3 lg:grid-cols-2 xl:grid-cols-1">
          <div className="glass-strong min-w-0 rounded-lg p-3">
            <p className="mb-2 text-sm font-semibold text-zinc-900">Priority findings</p>
            <div className="grid gap-1.5 sm:grid-cols-2">
              {(opportunities.length ? opportunities : [{ label: 'No PageSpeed opportunities returned', detail: 'The model still receives compact metrics and headers for context.' }]).map(item => (
                <div key={item.label} className="rounded-lg border border-[#ead7c4] bg-[#fffaf6] px-3 py-1.5">
                  <p className="text-xs font-medium text-zinc-900">{item.label}</p>
                  <p className="mt-1 text-xs text-zinc-600">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-strong min-w-0 rounded-lg p-3">
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900"><Server className="h-4 w-4 text-emerald-700" />HTTP headers</p>
            <dl className="grid gap-1.5">
              {(headers.length ? headers : [['Headers', snapshot?.http_headers?.error ?? 'No header snapshot available']]).map(header => (
                <div key={header[0]} className="grid gap-1 rounded-lg border border-[#ead7c4] bg-[#fffaf6] px-3 py-1.5 sm:grid-cols-[9rem_minmax(0,1fr)] sm:items-center">
                  <dt className="text-xs font-medium text-zinc-500">{header[0]}</dt>
                  <dd className="break-words text-xs font-semibold text-zinc-900">{header[1]}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>}
    </section>
  );
}

export function SEOWorkspaceView({ siteUrl, onSummaryChange }: SEOWorkspaceViewProps) {
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
  const [auditSnapshot, setAuditSnapshot] = useState<AuditSnapshot | null>(null);
  const [auditLoading, setAuditLoading] = useState(true);
  const [auditError, setAuditError] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState('mobile');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  const reportAreaRef = useRef<HTMLDivElement | null>(null);
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

  const loadAuditSnapshot = useCallback(async (signal?: AbortSignal) => {
    setAuditLoading(true);
    setAuditError('');
    try {
      const snapshot = await apiClient.get<AuditSnapshot>(`/seo/audit-snapshot?${siteQuery}`, { signal });
      if (!mounted.current || signal?.aborted) return;
      setAuditSnapshot(snapshot);
      const strategies = Object.keys(snapshot.core_web_vitals?.strategies ?? {});
      setSelectedStrategy(current => strategies.includes(current) ? current : strategies[0] ?? 'mobile');
    } catch (err) {
      if (!mounted.current || signal?.aborted) return;
      setAuditSnapshot(null);
      setAuditError(err instanceof Error ? err.message : 'Could not load Core Web Vitals.');
    } finally {
      if (mounted.current && !signal?.aborted) setAuditLoading(false);
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

  useEffect(() => {
    const audit = new AbortController();
    const timeout = window.setTimeout(() => {
      void loadAuditSnapshot(audit.signal);
    }, 0);
    return () => {
      window.clearTimeout(timeout);
      audit.abort();
    };
  }, [loadAuditSnapshot]);

  useEffect(() => {
    onSummaryChange?.(workspace ? workspaceHeaderSummary(workspace) : null);
  }, [onSummaryChange, workspace]);

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
    window.requestAnimationFrame(() => {
      reportAreaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    const abort = new AbortController();
    controller.current = abort;
    try {
      const response = await fetch(`${API_BASE_URL}/agent/weekly`, {
        method: 'POST', credentials: 'include', cache: 'no-store', signal: abort.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_url: siteUrl, website_number_of_pages: size, website_type: type, user_goal: goal,
          mode, focus: buildFocusPayload(focus), competitor_urls: competitorUrls,
          audit_snapshot: auditSnapshot?.compact_context ?? null,
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
    {error && <div role="alert" className="glass-strong flex items-start gap-2 rounded-lg border-red-200 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span></div>}
    {loading ? <p role="status" className="glass rounded-lg px-4 py-10 text-sm text-zinc-600">Loading saved work...</p> : !workspace ?
      <button onClick={() => window.location.reload()} className="glass-strong flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-emerald-800"><RefreshCw className="h-4 w-4" />Retry</button> : <>
      <form onSubmit={startAnalysis} className="glass rounded-lg p-4 sm:p-5">
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
      <AuditSnapshotPanel
        snapshot={auditSnapshot}
        loading={auditLoading}
        error={auditError}
        selectedStrategy={selectedStrategy}
        onStrategyChange={setSelectedStrategy}
        onRetry={() => void loadAuditSnapshot()}
      />
      <div ref={reportAreaRef} className="scroll-mt-24 space-y-6">
      {busy && <p role="status" className="glass-strong flex items-center gap-2 rounded-lg px-4 py-3 text-sm text-emerald-800"><LoaderCircle className="h-4 w-4 animate-spin" />{status || 'Review in progress...'}</p>}
      {!workspace.latest_report && !busy && <p className="glass rounded-lg px-4 py-5 text-sm text-zinc-600">Ready for the first saved review on this property.</p>}
      {workspace.latest_report && <div className="grid min-w-0 items-start gap-8 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <section className="glass min-w-0 space-y-5 rounded-lg p-4 sm:p-5">
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
        <div className="glass min-w-0 rounded-lg p-4 sm:p-5">
          <SEOTaskList tasks={workspace.tasks} disabled={saving || busy} onChange={updateTask} />
        </div>
      </div>}
      </div>
    </>}
  </div>;
}
