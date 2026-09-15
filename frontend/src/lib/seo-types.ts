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
