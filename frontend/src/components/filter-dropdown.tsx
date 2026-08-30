'use client';

import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';

interface FilterOption {
  value: string;
  label: string;
  icon?: string;
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
    <StyledWrapper ref={wrapperRef}>
      <label className="filter-label">{label}</label>
      <div className={`filter-container ${error ? 'error' : ''}`}>
        <button
          type="button"
          className="filter-trigger"
          onClick={() => setIsOpen(!isOpen)}
        >
          <span className={value ? 'selected' : 'placeholder'}>
            {displayValue}
          </span>
          <svg
            className={`arrow ${isOpen ? 'open' : ''}`}
            width="12"
            height="12"
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

        {isOpen && (
          <div className="input">
            {!showOtherInput ? (
              <>
                {options.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`value ${value === option.value ? 'active' : ''}`}
                    onClick={() => handleSelect(option.value)}
                  >
                    {option.icon && (
                      <span dangerouslySetInnerHTML={{ __html: option.icon }} />
                    )}
                    {option.label}
                  </button>
                ))}
                {allowOther && (
                  <button
                    type="button"
                    className="value"
                    onClick={() => handleSelect('other')}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="12" y1="5" x2="12" y2="19"></line>
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Other (specify)
                  </button>
                )}
              </>
            ) : (
              <div className="other-input-container">
                <input
                  type="text"
                  className="other-input"
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
                />
                <div className="other-input-actions">
                  <button
                    type="button"
                    className="other-btn submit"
                    onClick={handleOtherSubmit}
                  >
                    ✓
                  </button>
                  <button
                    type="button"
                    className="other-btn cancel"
                    onClick={() => {
                      setShowOtherInput(false);
                      setOtherValue('');
                    }}
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: relative;

  .filter-label {
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
  }

  .filter-container {
    position: relative;

    &.error .filter-trigger {
      border-color: #ef4444;
      box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
    }
  }

  .filter-trigger {
    width: 100%;
    padding: 0.625rem 0.875rem;
    background: #0a0a0b;
    border: 1px solid rgba(79, 70, 229, 0.3);
    border-radius: 6px;
    font-size: 0.8125rem;
    color: #ffffff;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;

    &:hover {
      border-color: rgba(79, 70, 229, 0.5);
      background: rgba(79, 70, 229, 0.05);
    }

    &:focus {
      outline: none;
      border-color: #4f46e5;
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
    }

    .placeholder {
      color: #8b8b8d;
    }

    .selected {
      color: #ffffff;
    }

    .arrow {
      color: #8b8b8d;
      transition: transform 0.2s;

      &.open {
        transform: rotate(180deg);
      }
    }
  }

  .input {
    position: absolute;
    top: calc(100% + 0.5rem);
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    background-color: rgba(10, 10, 11, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(79, 70, 229, 0.2);
    border-radius: 6px;
    padding: 6px;
    z-index: 50;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(79, 70, 229, 0.1);
    max-height: 180px;
    overflow-y: auto;
    animation: slideDown 0.2s ease-out;

    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateY(-10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  }

  .value {
    font-size: 13px;
    background-color: transparent;
    border: none;
    padding: 10px;
    color: #ffffff;
    display: flex;
    position: relative;
    gap: 8px;
    align-items: center;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.15s;
    box-sizing: border-box;

    &:hover {
      background-color: rgba(79, 70, 229, 0.15);
    }

    &:focus,
    &:active,
    &.active {
      background-color: rgba(79, 70, 229, 0.2);
      color: #a5b4fc;
      outline: none;
    }

    svg {
      width: 18px;
      height: 18px;
      flex-shrink: 0;
    }
  }

  .other-input-container {
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .other-input {
    width: 100%;
    padding: 10px;
    background-color: #0a0a0b;
    border: 1px solid rgba(79, 70, 229, 0.4);
    border-radius: 4px;
    color: #ffffff;
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: #4f46e5;
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
    }

    &::placeholder {
      color: #8b8b8d;
    }
  }

  .other-input-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .other-btn {
    padding: 6px 12px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;

    &.submit {
      background: linear-gradient(135deg, #4f46e5, #7c3aed);
      color: white;

      &:hover {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
      }
    }

    &.cancel {
      background-color: rgba(139, 139, 141, 0.1);
      color: #8b8b8d;

      &:hover {
        background-color: rgba(139, 139, 141, 0.2);
        color: #ffffff;
      }
    }
  }
`;
