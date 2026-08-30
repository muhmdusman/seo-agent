'use client';

import React, { useState, useRef, useEffect } from 'react';

interface PremiumSearchInputProps {
  sites: Array<{ siteUrl: string }>;
  onSelect: (siteUrl: string) => void;
  selectedSite: string;
  error?: boolean;
}

export function PremiumSearchInput({ sites, onSelect, selectedSite, error = false }: PremiumSearchInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredSites = sites.filter(site =>
    site.siteUrl.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelect = (siteUrl: string) => {
    onSelect(siteUrl);
    setIsOpen(false);
    setSearchTerm('');
  };

  return (
    <div ref={wrapperRef} className="relative w-full">
      {/* Main Input Container */}
      <div className={`relative flex items-center w-full h-12 rounded-lg bg-[#0a0a0b] border transition-all duration-200 ${
        error 
          ? 'border-red-500 shadow-[0_0_0_3px_rgba(239,68,68,0.1)]' 
          : 'border-indigo-500/30 hover:border-indigo-500/50 focus-within:border-indigo-500 focus-within:shadow-[0_0_0_3px_rgba(79,70,229,0.2)]'
      }`}>
        {/* Search Icon */}
        <div className="absolute left-4 pointer-events-none text-slate-400">
          <svg xmlns="http://www.w3.org/2000/svg" width={20} height={20} viewBox="0 0 24 24" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" fill="none" className="text-indigo-400">
            <circle cx={11} cy={11} r={8} stroke="currentColor" />
            <line x1={22} y1={22} x2="16.65" y2="16.65" stroke="currentColor" />
          </svg>
        </div>

        {/* Input Field */}
        <input
          type="text"
          placeholder={selectedSite || "Search properties..."}
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          className="flex-1 h-full bg-transparent border-none outline-none text-white text-sm pl-12 pr-24 placeholder:text-slate-500"
        />

        {/* Analyze Button */}
        <button
          type="button"
          className="absolute right-2 px-4 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold rounded-md transition-all duration-200 hover:shadow-lg hover:shadow-indigo-500/50"
        >
          Analyze
        </button>
      </div>

      {/* Dropdown List */}
      {isOpen && filteredSites.length > 0 && (
        <div className="absolute top-full mt-2 left-0 right-0 z-50 max-h-60 overflow-y-auto bg-[#0a0a0b]/95 backdrop-blur-xl border border-indigo-500/20 rounded-lg shadow-2xl">
          {filteredSites.map((site) => (
            <button
              key={site.siteUrl}
              type="button"
              onClick={() => handleSelect(site.siteUrl)}
              className={`w-full text-left px-4 py-3 text-sm text-white hover:bg-indigo-500/15 transition-colors duration-150 first:rounded-t-lg last:rounded-b-lg ${
                selectedSite === site.siteUrl ? 'bg-indigo-500/20 text-indigo-300' : ''
              }`}
            >
              {site.siteUrl}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
