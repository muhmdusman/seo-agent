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

export interface SEOTask {
  id: string;
  report_id: string;
  stage: string;
  title: string;
  priority: string;
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
  unavailable: 'Check unavailable',
};
