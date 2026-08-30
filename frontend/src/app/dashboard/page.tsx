'use client';

import { useEffect, useState } from 'react';
import { logout } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/config';
import { apiClient } from '@/lib/api-client';
import type { Site, SitesResponse } from '@/lib/types';
import { PremiumSearchInput } from '@/components/premium-search-input';
import { FilterDropdown } from '@/components/filter-dropdown';
import { TerminalLoader } from '@/components/terminal-loader';
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

const WEBSITE_SIZE_OPTIONS = [
  { value: '1-10', label: 'Micro (1-10 pages)' },
  { value: '11-30', label: 'Small (11-30 pages)' },
  { value: '31-100', label: 'Medium (31-100 pages)' },
  { value: '101-300', label: 'Large (101-300 pages)' },
  { value: '301+', label: 'Enterprise (301+ pages)' },
];

const WEBSITE_TYPE_OPTIONS = [
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'service-based', label: 'Service-based' },
  { value: 'content/publisher', label: 'Content/Publisher' },
  { value: 'saas', label: 'SaaS' },
  { value: 'other', label: 'Other' },
];

const USER_GOAL_OPTIONS = [
  { value: 'increase organic traffic', label: 'Increase Organic Traffic' },
  { value: 'increase conversions/sales', label: 'Increase Conversions/Sales' },
  { value: 'generate leads', label: 'Generate Leads' },
  { value: 'improve local visibility', label: 'Improve Local Visibility' },
  { value: 'build topical/brand authority', label: 'Build Topical/Brand Authority' },
  { value: 'other', label: 'Other' },
];

export default function DashboardPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [sitesLoading, setSitesLoading] = useState(true);
  const [selectedSite, setSelectedSite] = useState<string>('');
  const [websiteSize, setWebsiteSize] = useState<string>('');
  const [websiteType, setWebsiteType] = useState<string>('');
  const [userGoal, setUserGoal] = useState<string>('');
  const [validationErrors, setValidationErrors] = useState({
    site: false,
    size: false,
    type: false,
    goal: false,
  });
  const [status, setStatus] = useState<string>('');
  const [analysis, setAnalysis] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const accessToken = localStorage.getItem('access_token');
    
    if (!accessToken) {
      // No token at all, redirect to login
      window.location.href = '/';
      return;
    }

    // Token exists, try to use it
    fetchSites();
  }, []);

  async function fetchSites() {
    try {
      setSitesLoading(true);
      setError(null);
      const data = await apiClient.get<SitesResponse>('/search-console/sites');
      setSites(data.siteEntry ?? []);
      setError(null);
    } catch (err) {
      console.error('Error fetching sites:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load sites';
      
      // Don't set error if it's an auth error (user will be redirected by api-client)
      if (!errorMessage.includes('Authentication failed')) {
        setError(errorMessage);
      }
    } finally {
      setSitesLoading(false);
    }
  }

  function validateFilters(): boolean {
    const errors = {
      site: !selectedSite,
      size: !websiteSize,
      type: !websiteType,
      goal: !userGoal,
    };
    
    setValidationErrors(errors);
    
    return !Object.values(errors).some(err => err);
  }

  function handleAnalyzeClick() {
    if (!validateFilters()) {
      setError('Please select all required filters');
      return;
    }
    
    setError(null);
    handleStartAnalysis();
  }

  async function handleStartAnalysis() {
    const accessToken = localStorage.getItem('access_token');
    
    if (!accessToken) {
      setError('Please login again');
      window.location.href = '/';
      return;
    }

    // Decode token to get user_id (JWT tokens have payload in middle section)
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const userId = payload.sub || payload.user_id || payload.email;
      
      if (!userId) {
        setError('Invalid token. Please login again.');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/';
        return;
      }

      setAnalysis('');
      setError(null);
      setStatus('');
      setIsAnalyzing(true);

      const url = `${API_BASE_URL}/agent/weekly?user_id=${encodeURIComponent(
        userId
      )}&site_url=${encodeURIComponent(selectedSite)}&website_number_of_pages=${encodeURIComponent(
        websiteSize
      )}&website_type=${encodeURIComponent(websiteType)}&user_goal=${encodeURIComponent(
        userGoal
      )}`;

      console.log('Fetching analysis from:', url);
      const res = await fetch(url, { credentials: 'include' });

      if (!res.ok || !res.body) {
        console.error('Failed to start analysis:', res.status, res.statusText);
        setError('Failed to start analysis');
        setIsAnalyzing(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let hasReceivedAnalysis = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('Stream completed');
          setIsAnalyzing(false);
          break;
        }

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

            console.log('Received message:', message.substring(0, 100) + (message.length > 100 ? '...' : ''));

            if (KNOWN_STATUSES.includes(message)) {
              console.log('Setting status:', message);
              setStatus(message);
              if (message === 'Completed.') {
                console.log('Analysis completed, stopping spinner');
                setIsAnalyzing(false);
              }
            } else {
              console.log('Setting analysis (length):', message.length);
              setAnalysis(message);
              hasReceivedAnalysis = true;
              console.log('Analysis received, hiding spinner now');
              setIsAnalyzing(false);
            }
          } catch (err) {
            console.error('Failed to parse SSE message:', err, 'Payload:', payload);
          }
        }
      }

      setIsAnalyzing(false);
    } catch (err) {
      console.error('Analysis failed with error:', err);
      setError('Analysis failed');
      setIsAnalyzing(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-slate-900/80 border-b border-slate-700/50">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 py-3.5">
          <div className="flex items-center gap-2 sm:gap-3">
            <BrandMark className="h-8 w-8 sm:h-9 sm:w-9" />
            <div className="flex flex-col">
              <span className="text-xs sm:text-sm font-semibold leading-tight text-white">
                Search Console Agent
              </span>
              <span className="text-[10px] sm:text-xs leading-tight text-slate-400">
                Weekly SEO analysis
              </span>
            </div>
          </div>

          <Button 
            variant="secondary" 
            size="sm" 
            onClick={() => logout()}
            className="bg-slate-800 hover:bg-slate-700 text-white border-slate-700 text-xs sm:text-sm"
          >
            Log out
          </Button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 px-4 sm:px-6 py-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Analyze Your SEO Performance
          </h1>
          <p className="text-xs leading-relaxed text-slate-400">
            Pick a verified Search Console property and configure your analysis preferences.
          </p>
        </div>

        {sitesLoading ? (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-800/50 border border-slate-700">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-indigo-500" />
            <span className="text-xs sm:text-sm text-slate-400">Loading properties...</span>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Site Selection */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Search Console Property *
              </label>
              <PremiumSearchInput
                sites={sites}
                onSelect={(siteUrl) => {
                  setSelectedSite(siteUrl);
                  setValidationErrors(prev => ({ ...prev, site: false }));
                }}
                selectedSite={selectedSite}
                error={validationErrors.site}
              />
              {validationErrors.site && (
                <p className="text-xs text-red-400">Please select a property</p>
              )}
            </div>

            {/* Filters Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <FilterDropdown
                label="Website Size *"
                options={WEBSITE_SIZE_OPTIONS}
                value={websiteSize}
                onChange={(value) => {
                  setWebsiteSize(value);
                  setValidationErrors(prev => ({ ...prev, size: false }));
                }}
                placeholder="Select size"
                error={validationErrors.size}
              />

              <FilterDropdown
                label="Website Type *"
                options={WEBSITE_TYPE_OPTIONS}
                value={websiteType}
                onChange={(value) => {
                  setWebsiteType(value);
                  setValidationErrors(prev => ({ ...prev, type: false }));
                }}
                placeholder="Select type"
                error={validationErrors.type}
                allowOther
              />

              <FilterDropdown
                label="Primary Goal *"
                options={USER_GOAL_OPTIONS}
                value={userGoal}
                onChange={(value) => {
                  setUserGoal(value);
                  setValidationErrors(prev => ({ ...prev, goal: false }));
                }}
                placeholder="Select goal"
                error={validationErrors.goal}
                allowOther
              />
            </div>

            {/* Analyze Button */}
            <div className="flex justify-center pt-2">
              <button
                onClick={handleAnalyzeClick}
                disabled={isAnalyzing}
                className="group relative w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] text-white text-sm font-semibold rounded-md shadow-lg hover:shadow-indigo-500/50 transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 border border-purple-500/30"
              >
                <span className="relative z-10">
                  {isAnalyzing ? 'Analyzing...' : 'Analyze SEO Performance'}
                </span>
                <div className="absolute inset-0 rounded-md bg-gradient-to-r from-indigo-400 to-purple-400 opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
              </button>
            </div>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-900/20 p-4 backdrop-blur-sm"
          >
            <svg
              viewBox="0 0 20 20"
              aria-hidden="true"
              fill="currentColor"
              className="mt-0.5 h-4 w-4 shrink-0 text-red-400"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm0-12a.75.75 0 0 1 .75.75v4a.75.75 0 0 1-1.5 0v-4A.75.75 0 0 1 10 6Zm0 8.25a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-200">{error}</p>
          </div>
        )}

        {isAnalyzing && <TerminalLoader status={status} />}

        {!isAnalyzing && analysis && (
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 backdrop-blur-sm p-6">
            <AnalysisDisplay siteUrl={selectedSite} analysis={analysis} />
          </div>
        )}
      </main>
    </div>
  );
}
