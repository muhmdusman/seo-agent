export type AnalysisMode = 'auto' | 'review' | 'growth';

export const ANALYSIS_MODE_LABELS: Record<AnalysisMode, string> = {
  auto: 'SEO review & fixes',
  review: 'Check changes and their results',
  growth: 'Opportunities to get more visibility',
};

export interface SEOPerformanceMetrics {
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface SEOTaskReview {
  task_id: string;
  title: string;
  status: 'observed' | 'not_observed' | 'manual_review' | 'unavailable';
  detail: string;
  checked_at: string;
  url?: string;
  condition?: { field: string; expected: string } | null;
  observed_value?: string | number | boolean | string[] | null;
  changed_fields?: string[];
  performance?: {
    status: string;
    detail?: string;
    before?: SEOPerformanceMetrics;
    after?: SEOPerformanceMetrics;
    windows?: { before: { start: string; end: string }; after: { start: string; end: string } };
  };
}

export interface SEOReport {
  id: string;
  site_url: string;
  report: string;
  summary: string;
  created_at: string;
  stages: string[];
  preferences: {
    website_number_of_pages?: string;
    website_type?: string;
    user_goal?: string;
    mode?: AnalysisMode;
    focus?: string;
    competitor_urls?: string[];
  };
  evidence?: {
    core_web_vitals?: CompactCoreWebVitals | null;
    reviews?: SEOTaskReview[];
    limitations?: string[];
    task_generation?: {
      candidate: number;
      created: number;
      reused: number;
      already_observed: number;
    };
  };
}

export interface MetricSnapshot {
  key?: string;
  label?: string;
  value?: number | null;
  unit?: string;
  display_value?: string;
  category?: string;
  score?: number | null;
}

export interface PageSpeedStrategySnapshot {
  strategy: 'mobile' | 'desktop' | string;
  requested_url?: string;
  final_url?: string;
  fetch_time?: string;
  lighthouse_version?: string;
  overall_category?: string;
  origin_fallback?: boolean;
  scores: {
    performance?: number | null;
    accessibility?: number | null;
    best_practices?: number | null;
    seo?: number | null;
  };
  field: Record<string, MetricSnapshot>;
  lab: Record<string, MetricSnapshot>;
  opportunities?: { id: string; label: string; detail: string; score?: number | null; savings_ms?: number }[];
  warnings?: string[];
}

export interface CompactCoreWebVitals {
  status?: string;
  collected_at?: string;
  url?: string;
  strategies?: Record<string, {
    scores?: PageSpeedStrategySnapshot['scores'];
    field?: Record<string, MetricSnapshot>;
    lab?: Record<string, MetricSnapshot>;
  }>;
  errors?: Record<string, string>;
  error?: string;
}

export interface HttpHeaderSnapshot {
  status?: string;
  checked_at?: string;
  requested_url?: string;
  final_url?: string;
  status_code?: number;
  http_version?: string;
  headers?: Record<string, string>;
  redirects?: { status_code: number; location: string }[];
  error?: string;
}

export interface AuditSnapshot {
  site_url: string;
  url: string;
  collected_at: string;
  core_web_vitals: {
    status?: string;
    collected_at?: string;
    url?: string;
    strategies?: Record<string, PageSpeedStrategySnapshot>;
    errors?: Record<string, string>;
    error?: string;
  };
  http_headers: HttpHeaderSnapshot;
  compact_context: {
    core_web_vitals?: CompactCoreWebVitals | null;
    http_headers?: HttpHeaderSnapshot | null;
  };
}

export interface SEOTask {
  id: string;
  report_id: string;
  stage: string;
  title: string;
  priority: string;
  target_platform: string;
  scope: string;
  evidence: string;
  why_it_matters: string;
  manual_fix: string;
  agent_prompt: string;
  completed_at: string | null;
  verification?: {
    field: 'title' | 'meta_description' | 'canonical' | 'h1' | 'noindex' | 'viewport' | 'status_code';
    expected: string;
  } | null;
  review?: SEOTaskReview | null;
  implementation?: {
    status: 'pending' | 'running' | 'proposed' | 'applied' | 'pr_created' | 'blocked' | 'failed';
    attempts: number;
    branch: string;
    diff: string;
    result: {
      commit?: string;
      preview_path?: string;
      pull_request?: { number?: number; url?: string; state?: string };
      sandbox_tests?: Record<string, string>;
    } | null;
    error: string;
    started_at: string | null;
    completed_at: string | null;
  };
  subtasks: { id: string; title: string; completed_at: string | null }[];
}

export interface SEOWorkspace {
  site_url: string;
  latest_report: SEOReport | null;
  tasks: SEOTask[];
  covered_stages: string[];
  pending_count: number;
  running: boolean;
  can_analyze: boolean;
  framework_complete: boolean;
  next_stages: string[];
  phase: 'framework' | 'visibility-opportunities' | 'review-results';
  next_review_at?: string | null;
}

export interface ReportHistory {
  reports: SEOReport[];
  next_offset: number | null;
}

export const STAGE_LABELS: Record<string, string> = {
  'technical-foundation': 'Technical Foundation',
  crawlability: 'Crawlability',
  rendering: 'Rendering',
  indexability: 'Indexability',
  'on-page': 'On-Page SEO',
  content: 'Content',
  'search-intent': 'Search Intent',
  'semantic-seo': 'Semantic SEO',
  'ai-geo': 'AI / GEO',
};

export function slugLabel(value: string): string {
  const words = value.replace(/[-_]+/g, ' ').trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] ?? slugLabel(stage);
}

export const REVIEW_LABELS: Record<SEOTaskReview['status'], string> = {
  observed: 'Saved condition observed',
  not_observed: 'Saved condition not observed',
  manual_review: 'Manual review needed',
  unavailable: 'Evidence queued',
};
