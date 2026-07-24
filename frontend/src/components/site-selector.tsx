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
    return <div className="text-sm text-gray-500">Loading sites...</div>;
  }

  if (error) {
    return <div className="text-sm text-red-500">{error}</div>;
  }

  if (sites.length === 0) {
    return (
      <div className="text-sm text-gray-500">
        No sites found. Please add sites to your Google Search Console.
      </div>
    );
  }

  return (
    <Select onValueChange={onSiteSelect}>
      <SelectTrigger className="w-full max-w-md">
        <SelectValue placeholder="Select a site to analyze" />
      </SelectTrigger>
      <SelectContent>
        {sites.map((site) => (
          <SelectItem key={site.siteUrl} value={site.siteUrl}>
            {site.siteUrl}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
