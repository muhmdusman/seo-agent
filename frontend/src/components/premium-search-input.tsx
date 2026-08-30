'use client';

import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';

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
    <StyledWrapper ref={wrapperRef}>
      <div className="grid" />
      <div id="poda" className={error ? 'error' : ''}>
        <div className="glow" />
        <div className="darkBorderBg" />
        <div className="darkBorderBg" />
        <div className="darkBorderBg" />
        <div className="white" />
        <div className="border" />
        <div id="main">
          <input
            placeholder={selectedSite || "Search properties..."}
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            className="input"
          />
          <div id="input-mask" />
          <div id="pink-mask" />
          <div className="filterBorder" />
          <div id="analyze-button">
            Analyze
          </div>
          <div id="search-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width={24} viewBox="0 0 24 24" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" height={24} fill="none" className="feather feather-search">
              <circle stroke="url(#search)" r={8} cy={11} cx={11} />
              <line stroke="url(#searchl)" y2="16.65" y1={22} x2="16.65" x1={22} />
              <defs>
                <linearGradient gradientTransform="rotate(50)" id="search">
                  <stop stopColor="#f8e7f8" offset="0%" />
                  <stop stopColor="#b6a9b7" offset="50%" />
                </linearGradient>
                <linearGradient id="searchl">
                  <stop stopColor="#b6a9b7" offset="0%" />
                  <stop stopColor="#837484" offset="50%" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {isOpen && filteredSites.length > 0 && (
            <div className="dropdown">
              {filteredSites.map((site) => (
                <button
                  key={site.siteUrl}
                  type="button"
                  className={`dropdown-item ${selectedSite === site.siteUrl ? 'selected' : ''}`}
                  onClick={() => handleSelect(site.siteUrl)}
                >
                  {site.siteUrl}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  position: relative;
  width: 100%;
  max-width: 600px;

  .grid {
    height: 800px;
    width: 800px;
    background-image: linear-gradient(to right, #0f0f10 1px, transparent 1px),
      linear-gradient(to bottom, #0f0f10 1px, transparent 1px);
    background-size: 1rem 1rem;
    background-position: center center;
    position: absolute;
    z-index: -1;
    filter: blur(1px);
    pointer-events: none;
  }

  .white,
  .border,
  .darkBorderBg,
  .glow {
    max-height: 50px;
    max-width: 100%;
    height: 100%;
    width: 100%;
    position: absolute;
    overflow: hidden;
    z-index: -1;
    border-radius: 6px;
    filter: blur(3px);
  }

  .input {
    background-color: #0a0a0b;
    border: none;
    width: 100%;
    height: 48px;
    border-radius: 6px;
    color: #ffffff;
    padding-inline: 50px;
    font-size: 14px;
  }

  #poda {
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;

    &.error .white::before,
    &.error .border::before,
    &.error .darkBorderBg::before,
    &.error .glow::before {
      background-image: conic-gradient(
        rgba(0, 0, 0, 0) 0%,
        #ff4444,
        rgba(0, 0, 0, 0) 8%,
        rgba(0, 0, 0, 0) 50%,
        #ff6666,
        rgba(0, 0, 0, 0) 58%
      ) !important;
    }
  }

  .input::placeholder {
    color: #8b8b8d;
  }

  .input:focus {
    outline: none;
  }

  #main:focus-within > #input-mask {
    display: none;
  }

  #input-mask {
    pointer-events: none;
    width: 100px;
    height: 20px;
    position: absolute;
    background: linear-gradient(90deg, transparent, #0a0a0b);
    top: 14px;
    left: 60px;
  }

  #pink-mask {
    pointer-events: none;
    width: 30px;
    height: 20px;
    position: absolute;
    background: #8b5cf6;
    top: 8px;
    left: 5px;
    filter: blur(20px);
    opacity: 0.6;
    transition: all 2s;
  }

  #main:hover > #pink-mask {
    opacity: 0;
  }

  .white {
    max-height: 46px;
    border-radius: 6px;
    filter: blur(2px);
  }

  .white::before {
    content: "";
    z-index: -2;
    text-align: center;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(83deg);
    position: absolute;
    width: 600px;
    height: 600px;
    background-repeat: no-repeat;
    background-position: 0 0;
    filter: brightness(1.2);
    background-image: conic-gradient(
      rgba(0, 0, 0, 0) 0%,
      #6366f1,
      rgba(0, 0, 0, 0) 8%,
      rgba(0, 0, 0, 0) 50%,
      #8b5cf6,
      rgba(0, 0, 0, 0) 58%
    );
    transition: all 2s;
  }

  .border {
    max-height: 48px;
    border-radius: 6px;
    filter: blur(0.5px);
  }

  .border::before {
    content: "";
    z-index: -2;
    text-align: center;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(70deg);
    position: absolute;
    width: 600px;
    height: 600px;
    filter: brightness(1.1);
    background-repeat: no-repeat;
    background-position: 0 0;
    background-image: conic-gradient(
      #0a0a0b,
      #4f46e5 5%,
      #0a0a0b 14%,
      #0a0a0b 50%,
      #7c3aed 60%,
      #0a0a0b 64%
    );
    transition: all 2s;
  }

  .darkBorderBg {
    max-height: 52px;
  }

  .darkBorderBg::before {
    content: "";
    z-index: -2;
    text-align: center;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(82deg);
    position: absolute;
    width: 600px;
    height: 600px;
    background-repeat: no-repeat;
    background-position: 0 0;
    background-image: conic-gradient(
      rgba(0, 0, 0, 0),
      #312e81,
      rgba(0, 0, 0, 0) 10%,
      rgba(0, 0, 0, 0) 50%,
      #581c87,
      rgba(0, 0, 0, 0) 60%
    );
    transition: all 2s;
  }

  #poda:hover > .darkBorderBg::before {
    transform: translate(-50%, -50%) rotate(-98deg);
  }

  #poda:hover > .glow::before {
    transform: translate(-50%, -50%) rotate(-120deg);
  }

  #poda:hover > .white::before {
    transform: translate(-50%, -50%) rotate(-97deg);
  }

  #poda:hover > .border::before {
    transform: translate(-50%, -50%) rotate(-110deg);
  }

  #poda:focus-within > .darkBorderBg::before {
    transform: translate(-50%, -50%) rotate(442deg);
    transition: all 4s;
  }

  #poda:focus-within > .glow::before {
    transform: translate(-50%, -50%) rotate(420deg);
    transition: all 4s;
  }

  #poda:focus-within > .white::before {
    transform: translate(-50%, -50%) rotate(443deg);
    transition: all 4s;
  }

  #poda:focus-within > .border::before {
    transform: translate(-50%, -50%) rotate(430deg);
    transition: all 4s;
  }

  .glow {
    overflow: hidden;
    filter: blur(30px);
    opacity: 0.3;
    max-height: 100px;
  }

  .glow:before {
    content: "";
    z-index: -2;
    text-align: center;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(60deg);
    position: absolute;
    width: 999px;
    height: 999px;
    background-repeat: no-repeat;
    background-position: 0 0;
    background-image: conic-gradient(
      #000,
      #4f46e5 5%,
      #000 38%,
      #000 50%,
      #7c3aed 60%,
      #000 87%
    );
    transition: all 2s;
  }

  #analyze-button {
    position: absolute;
    top: 6px;
    right: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2;
    max-height: 36px;
    max-width: 85px;
    height: 100%;
    width: 100%;
    cursor: pointer;
    isolation: isolate;
    overflow: hidden;
    border-radius: 4px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    border: 1px solid rgba(139, 92, 246, 0.3);
    color: white;
    font-size: 13px;
    font-weight: 600;
    transition: all 0.2s;

    &:hover {
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
    }
  }

  .filterBorder {
    height: 38px;
    width: 87px;
    position: absolute;
    overflow: hidden;
    top: 5px;
    right: 5px;
    border-radius: 4px;
    pointer-events: none;
  }

  .filterBorder::before {
    content: "";
    text-align: center;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(90deg);
    position: absolute;
    width: 600px;
    height: 600px;
    background-repeat: no-repeat;
    background-position: 0 0;
    filter: brightness(1.2);
    background-image: conic-gradient(
      rgba(0, 0, 0, 0),
      #4f46e5,
      rgba(0, 0, 0, 0) 50%,
      rgba(0, 0, 0, 0) 50%,
      #7c3aed,
      rgba(0, 0, 0, 0) 100%
    );
    animation: rotate 4s linear infinite;
  }

  @keyframes rotate {
    100% {
      transform: translate(-50%, -50%) rotate(450deg);
    }
  }

  #main {
    position: relative;
  }

  #search-icon {
    position: absolute;
    left: 16px;
    top: 12px;
    pointer-events: none;
  }

  .dropdown {
    position: absolute;
    top: calc(100% + 8px);
    left: 0;
    right: 0;
    background-color: rgba(10, 10, 11, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 6px;
    padding: 6px;
    z-index: 50;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(99, 102, 241, 0.1);
    max-height: 200px;
    overflow-y: auto;
  }

  .dropdown-item {
    width: 100%;
    text-align: left;
    padding: 10px;
    background: transparent;
    border: none;
    color: #ffffff;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.15s;
    font-size: 13px;

    &:hover {
      background-color: rgba(99, 102, 241, 0.15);
    }

    &.selected {
      background-color: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
    }
  }
`;
