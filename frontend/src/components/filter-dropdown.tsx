'use client';

import React, { useState, useRef, useEffect } from 'react';

interface FilterOption {
  value: string;
  label: string;
}

interface FilterDropdownProps {
  label: string;
  options: FilterOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: boolean;
  allowOther?: boolean;
}

export function FilterDropdown({
  label,
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  error = false,
  allowOther = false,
}: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [otherValue, setOtherValue] = useState('');
  const [showOtherInput, setShowOtherInput] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setShowOtherInput(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (optionValue: string) => {
    if (optionValue === 'other' && allowOther) {
      setShowOtherInput(true);
    } else {
      onChange(optionValue);
      setIsOpen(false);
      setShowOtherInput(false);
    }
  };

  const handleOtherSubmit = () => {
    if (otherValue.trim()) {
      onChange(otherValue.trim());
      setIsOpen(false);
      setShowOtherInput(false);
      setOtherValue('');
    }
  };

  const selectedOption = options.find(opt => opt.value === value);
  const displayValue = selectedOption ? selectedOption.label : value || placeholder;

  return (
    <div ref={wrapperRef} className="relative flex flex-col gap-2">
      {/* Label */}
      <label className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </label>

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between px-4 py-2.5 text-sm rounded-lg bg-[#0a0a0b] border transition-all duration-200 ${
          error
            ? 'border-red-500 shadow-[0_0_0_3px_rgba(239,68,68,0.1)]'
            : 'border-indigo-500/30 hover:border-indigo-500/50 hover:bg-indigo-500/5 focus:border-indigo-500 focus:shadow-[0_0_0_3px_rgba(79,70,229,0.2)] focus:outline-none'
        }`}
      >
        <span className={value ? 'text-white' : 'text-slate-500'}>
          {displayValue}
        </span>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          viewBox="0 0 12 12"
          fill="none"
        >
          <path
            d="M2.5 4.5L6 8L9.5 4.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full mt-2 left-0 right-0 z-50 max-h-60 overflow-y-auto bg-[#0a0a0b]/95 backdrop-blur-xl border border-indigo-500/20 rounded-lg shadow-2xl">
          {!showOtherInput ? (
            <>
              {options.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  className={`w-full text-left px-4 py-2.5 text-sm text-white hover:bg-indigo-500/15 transition-colors duration-150 first:rounded-t-lg ${
                    value === option.value ? 'bg-indigo-500/20 text-indigo-300' : ''
                  }`}
                >
                  {option.label}
                </button>
              ))}
              {allowOther && (
                <button
                  type="button"
                  onClick={() => handleSelect('other')}
                  className="w-full text-left px-4 py-2.5 text-sm text-white hover:bg-indigo-500/15 transition-colors duration-150 last:rounded-b-lg flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                  </svg>
                  Other (specify)
                </button>
              )}
            </>
          ) : (
            <div className="p-3 space-y-2">
              <input
                type="text"
                placeholder="Enter your value..."
                value={otherValue}
                onChange={(e) => setOtherValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleOtherSubmit();
                  } else if (e.key === 'Escape') {
                    setShowOtherInput(false);
                    setOtherValue('');
                  }
                }}
                autoFocus
                className="w-full px-3 py-2 bg-[#0a0a0b] border border-indigo-500/40 rounded-md text-white text-sm placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:shadow-[0_0_0_3px_rgba(79,70,229,0.2)]"
              />
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={handleOtherSubmit}
                  className="px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold rounded-md transition-all duration-200"
                >
                  ✓ Confirm
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowOtherInput(false);
                    setOtherValue('');
                  }}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold rounded-md transition-all duration-200"
                >
                  ✕ Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
