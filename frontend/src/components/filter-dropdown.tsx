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
    color: #64748b;
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
    padding: 0.75rem 1rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    color: #1e293b;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;

    &:hover {
      border-color: #cbd5e1;
    }

    &:focus {
      outline: none;
      border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }

    .placeholder {
      color: #94a3b8;
    }

    .selected {
      color: #1e293b;
    }

    .arrow {
      color: #64748b;
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
    background-color: #0d1117;
    border-radius: 10px;
    padding: 10px;
    z-index: 50;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    max-height: 300px;
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
    font-size: 15px;
    background-color: transparent;
    border: none;
    padding: 10px;
    color: white;
    display: flex;
    position: relative;
    gap: 8px;
    align-items: center;
    cursor: pointer;
    border-radius: 10px;
    transition: all 0.3s;
    box-sizing: border-box;

    &:hover {
      border: 2px solid #1a1f24;
      color: #637185;
    }

    &:focus,
    &:active,
    &.active {
      background-color: #1a1f24;
      outline: none;
      margin-left: 17px;

      &::before {
        opacity: 1;
      }
    }

    &::before {
      content: "";
      position: absolute;
      top: 5px;
      left: -15px;
      width: 5px;
      height: 80%;
      background-color: #2f81f7;
      border-radius: 5px;
      opacity: 0;
      transition: opacity 0.3s;
    }

    svg {
      width: 20px;
      height: 20px;
      flex-shrink: 0;
    }
  }

  .input:hover > .value:not(:hover) {
    transition: 300ms;
    filter: blur(1.5px);
    transform: scale(0.95, 0.95);
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
    background-color: #1a1f24;
    border: 1px solid #2f81f7;
    border-radius: 8px;
    color: white;
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: #4f94ff;
    }

    &::placeholder {
      color: #637185;
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
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;

    &.submit {
      background-color: #2f81f7;
      color: white;

      &:hover {
        background-color: #4f94ff;
      }
    }

    &.cancel {
      background-color: #1a1f24;
      color: #637185;

      &:hover {
        background-color: #2a2f34;
        color: white;
      }
    }
  }
`;
