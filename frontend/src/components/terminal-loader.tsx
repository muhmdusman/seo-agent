'use client';

import React from 'react';
import styled from 'styled-components';

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
    <StyledWrapper>
      <div className="terminal-loader">
        <div className="terminal-header">
          <div className="terminal-title">Status</div>
          <div className="terminal-controls">
            <div className="control close" />
            <div className="control minimize" />
            <div className="control maximize" />
          </div>
        </div>
        <div className="text">{displayText}</div>
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem 0;

  @keyframes blinkCursor {
    50% {
      border-right-color: transparent;
    }
  }

  @keyframes typeAndDelete {
    0%,
    10% {
      width: 0;
    }
    45%,
    55% {
      width: 100%;
    }
    90%,
    100% {
      width: 0;
    }
  }

  .terminal-loader {
    border: 0.1em solid #333;
    background-color: #1a1a1a;
    color: #0f0;
    font-family: "Courier New", Courier, monospace;
    font-size: 1em;
    padding: 1.5em 1em;
    width: 20em;
    max-width: 90%;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    position: relative;
    overflow: hidden;
    box-sizing: border-box;
  }

  .terminal-header {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1.5em;
    background-color: #333;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 0 0.4em;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .terminal-controls {
    display: flex;
    gap: 0.4em;
  }

  .control {
    width: 0.6em;
    height: 0.6em;
    border-radius: 50%;
    background-color: #777;
  }

  .control.close {
    background-color: #e33;
  }

  .control.minimize {
    background-color: #ee0;
  }

  .control.maximize {
    background-color: #0b0;
  }

  .terminal-title {
    line-height: 1.5em;
    color: #eee;
    font-size: 0.8em;
  }

  .text {
    display: inline-block;
    white-space: nowrap;
    overflow: hidden;
    border-right: 0.2em solid #0f0;
    animation:
      typeAndDelete 4s steps(20) infinite,
      blinkCursor 0.5s step-end infinite alternate;
    margin-top: 1.5em;
    max-width: 100%;
  }
`;
