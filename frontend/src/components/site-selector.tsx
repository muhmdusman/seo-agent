/**
 * Site Selector Component
 * 
 * Fetches and displays Google Search Console sites in a dropdown selector.
 * Handles loading and error states, and triggers callback when a site is selected.
 */

'use client';

import { useState, useEffect } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { apiClient } from '@/lib/api-client';
import type { Site, SitesResponse } from '@/lib/types';

interface SiteSelectorProps {
  onSiteSelect: (siteUrl: string) => void;
}

export function SiteSelector({ onSiteSelect }: SiteSelectorProps) {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSites();
  }, []);

  async function fetchSites() {
    try {
      setLoading(true);
      setError(null);
      
      const data = await apiClient.get<SitesResponse>(
        '/search-console/sites'
      );
      
      setSites(data.siteEntry ?? []);
    } catch (err) {
      setError('Failed to load sites');
      console.error('Error fetching sites:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="glass-strong flex h-11 w-full max-w-md items-center gap-2.5 rounded-xl px-4 text-sm text-slate-500">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
        Loading properties...
      </div>
    );
  }

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-800">
        {error}
      </p>
    );
  }

  if (sites.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        No properties found. Add and verify a site in Google Search Console
        first.
      </p>
    );
  }

  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <label
        htmlFor="site-selector"
        className="text-xs font-medium uppercase tracking-wide text-slate-500"
      >
        Search Console property
      </label>
      <Select onValueChange={onSiteSelect}>
        <SelectTrigger id="site-selector" className="w-full">
          <SelectValue placeholder="Select a property to analyze" />
        </SelectTrigger>
        <SelectContent>
          {sites.map((site) => (
            <SelectItem key={site.siteUrl} value={site.siteUrl}>
              {site.siteUrl}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
