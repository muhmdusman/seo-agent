'use client';

import React from 'react';

interface TerminalLoaderProps {
  status?: string;
}

const statusMessages = {
  'Getting Google credentials...': 'Authenticating...',
  'Fetching Search Console...': 'Fetching data...',
  'Scraping website...': 'Analyzing site...',
  'Thinking...': 'Generating insights...',
  'default': 'Processing...'
};

export function TerminalLoader({ status }: TerminalLoaderProps) {
  const displayText = status ? (statusMessages[status as keyof typeof statusMessages] || statusMessages.default) : statusMessages.default;

  return (
    <div className="flex flex-col items-center justify-center py-12 gap-6">
      {/* Spinner */}
      <div className="relative w-16 h-16">
        {/* Outer rotating ring */}
        <div className="absolute inset-0 border-4 border-indigo-500/20 rounded-full"></div>
        
        {/* Animated gradient ring */}
        <div className="absolute inset-0 border-4 border-transparent border-t-indigo-500 border-r-purple-500 rounded-full animate-spin"></div>
        
        {/* Inner pulsing dot */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-3 h-3 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full animate-pulse"></div>
        </div>
      </div>

      {/* Status Text */}
      <div className="flex flex-col items-center gap-2">
        <p className="text-white text-lg font-medium">{displayText}</p>
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  );
}
