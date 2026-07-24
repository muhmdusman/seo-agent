# Design Document: SEO Dashboard Frontend

## Overview

The SEO Dashboard Frontend is a Next.js 14+ application using TypeScript, App Router, Tailwind CSS, and minimal shadcn/ui components. It implements Google OAuth 2.0 authentication with automatic token refresh, displays Google Search Console sites in a dropdown, and presents complete SEO analysis results from the backend agent.

## Architecture

### Technology Stack

- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui (Select, Button, Card only)
- **HTTP Client**: fetch API with custom interceptor
- **JWT Handling**: jose library for JWT decoding

### Application Structure

```
src/
├── app/
│   ├── page.tsx                 # Landing page (/)
│   ├── callback/
│   │   └── page.tsx             # OAuth callback (/callback)
│   ├── dashboard/
│   │   └── page.tsx             # Dashboard page (/dashboard)
│   └── layout.tsx               # Root layout
├── components/
│   ├── ui/
│   │   ├── button.tsx           # shadcn Button
│   │   ├── select.tsx           # shadcn Select
│   │   └── card.tsx             # shadcn Card
│   ├── site-selector.tsx        # Site dropdown component
│   ├── analysis-display.tsx     # Analysis results component
│   └── loading-spinner.tsx      # Custom loading indicator
├── lib/
│   ├── api-client.ts            # API client with interceptor
│   ├── token-manager.ts         # Token refresh logic
│   ├── auth.ts                  # Authentication utilities
│   └── types.ts                 # TypeScript type definitions
└── middleware.ts                # Route protection middleware
```

## Routing Architecture

### Page Structure

#### 1. Landing Page (`/`)
- **Route**: `app/page.tsx`
- **Purpose**: Entry point for unauthenticated users
- **Components**: Login button
- **Behavior**: Redirects authenticated users to dashboard

#### 2. Callback Page (`/callback`)
- **Route**: `app/callback/page.tsx`
- **Purpose**: Handles OAuth redirect from Google
- **Query Parameters**:
  - `status=success`: Redirect to `/dashboard`
  - `status=error`: Redirect to `/` with error message
- **Behavior**: Displays loading state while processing

#### 3. Dashboard Page (`/dashboard`)
- **Route**: `app/dashboard/page.tsx`
- **Purpose**: Main authenticated interface
- **Components**: Header with logout, Site_Selector, Analysis_Display
- **Protection**: Requires valid Access_Token cookie

### Route Protection Middleware

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const accessToken = request.cookies.get('access_token');
  const { pathname } = request.nextUrl;

  // Protect /dashboard route
  if (pathname.startsWith('/dashboard') && !accessToken) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Redirect authenticated users away from landing page
  if (pathname === '/' && accessToken) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/', '/dashboard/:path*'],
};
```

## API Client Architecture

### HTTP Client with Token Refresh Interceptor

The API client wraps the native fetch API with automatic token refresh on 401 responses.

```typescript
// lib/api-client.ts
import { TokenManager } from './token-manager';

interface ApiRequestOptions extends RequestInit {
  skipRefresh?: boolean;
}

class ApiClient {
  private baseUrl: string;
  private tokenManager: TokenManager;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.tokenManager = new TokenManager(this.baseUrl);
  }

  async request<T>(
    endpoint: string,
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      ...options,
      credentials: 'include', // Include cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && !options.skipRefresh) {
        const refreshed = await this.tokenManager.refresh();
        
        if (refreshed) {
          // Retry original request with new token
          return this.request<T>(endpoint, { ...options, skipRefresh: true });
        } else {
          // Refresh failed - redirect to login
          window.location.href = '/';
          throw new Error('Authentication failed');
        }
      }

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      return response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

export const apiClient = new ApiClient();
```

### Token Manager

Handles token refresh logic transparently.

```typescript
// lib/token-manager.ts
export class TokenManager {
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<boolean> | null = null;

  constructor(private baseUrl: string) {}

  async refresh(): Promise<boolean> {
    // Prevent concurrent refresh requests
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = this.performRefresh();

    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  private async performRefresh(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // Include refresh_token cookie
      });

      return response.ok;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  }
}
```

## Component Architecture

### 1. Site Selector Component

Dropdown for selecting Google Search Console sites.

```typescript
// components/site-selector.tsx
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
import type { Site } from '@/lib/types';

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
      const data = await apiClient.get<{ sites: Site[] }>(
        '/api/v1/search-console/sites'
      );
      setSites(data.sites);
    } catch (err) {
      setError('Failed to load sites');
      console.error(err);
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
```

### 2. Analysis Display Component

Renders markdown analysis results in a card.

```typescript
// components/analysis-display.tsx
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import ReactMarkdown from 'react-markdown';

interface AnalysisDisplayProps {
  siteUrl: string;
  analysis: string;
}

export function AnalysisDisplay({ siteUrl, analysis }: AnalysisDisplayProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>SEO Analysis for {siteUrl}</CardTitle>
      </CardHeader>
      <CardContent className="prose prose-sm max-w-none">
        <ReactMarkdown>{analysis}</ReactMarkdown>
      </CardContent>
    </Card>
  );
}
```

### 3. Loading Spinner Component

Custom loading indicator using Tailwind CSS.

```typescript
// components/loading-spinner.tsx
interface LoadingSpinnerProps {
  text?: string;
}

export function LoadingSpinner({ text = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
      <p className="text-sm text-gray-600">{text}</p>
    </div>
  );
}
```

## State Management

### React Hooks Strategy

The application uses React hooks for state management:

- **Local Component State**: `useState` for component-specific data
- **Side Effects**: `useEffect` for data fetching and subscriptions
- **No Global State**: Authentication state managed via cookies (httpOnly)
- **Data Flow**: Unidirectional from API → Component State → UI

### Dashboard State Flow

```typescript
// app/dashboard/page.tsx (simplified)
'use client';

export default function DashboardPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [selectedSite, setSelectedSite] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Extract user ID from JWT on mount
  useEffect(() => {
    const uid = getUserIdFromToken();
    if (!uid) {
      window.location.href = '/';
    } else {
      setUserId(uid);
    }
  }, []);

  // Fetch analysis when site is selected
  async function handleSiteSelect(siteUrl: string) {
    setSelectedSite(siteUrl);
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiClient.get<{ analysis: string }>(
        `/api/v1/agent/weekly?user_id=${userId}&site_url=${encodeURIComponent(siteUrl)}`
      );
      setAnalysis(result.analysis);
    } catch (err) {
      setError('Failed to fetch analysis');
    } finally {
      setLoading(false);
    }
  }

  return (
    // JSX with SiteSelector and AnalysisDisplay
  );
}
```

## Type Definitions

### API Response Types

```typescript
// lib/types.ts

export interface Site {
  siteUrl: string;
  permissionLevel: string;
}

export interface SitesResponse {
  sites: Site[];
}

export interface AnalysisResponse {
  analysis: string;
  site_url: string;
  generated_at: string;
}

export interface AuthTokenPayload {
  sub: string; // user_id
  exp: number;
  iat: number;
}

export interface ErrorResponse {
  detail: string;
}
```

## Authentication Flow

### JWT Token Management

```typescript
// lib/auth.ts
import { jwtDecode } from 'jose';
import type { AuthTokenPayload } from './types';

export function getUserIdFromToken(): string | null {
  try {
    // Access token is httpOnly, but we can decode it client-side
    // by reading it from a non-httpOnly duplicate or using a server action
    const token = getAccessTokenFromCookie();
    if (!token) return null;

    const payload = jwtDecode<AuthTokenPayload>(token);
    return payload.sub;
  } catch (error) {
    console.error('Failed to decode token:', error);
    return null;
  }
}

function getAccessTokenFromCookie(): string | null {
  // Implementation depends on whether we use a readable cookie
  // or server action to expose user_id
  const cookies = document.cookie.split('; ');
  const tokenCookie = cookies.find(c => c.startsWith('access_token='));
  return tokenCookie ? tokenCookie.split('=')[1] : null;
}

export async function logout(): Promise<void> {
  try {
    await fetch('/api/v1/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
  } finally {
    window.location.href = '/';
  }
}
```

### OAuth Flow Sequence

```
1. User clicks "Sign in with Google" on Landing Page
   ↓
2. Redirect to /api/v1/auth/google (backend)
   ↓
3. Google OAuth consent screen
   ↓
4. Google redirects to backend callback
   ↓
5. Backend sets httpOnly cookies (access_token, refresh_token)
   ↓
6. Backend redirects to /callback?status=success
   ↓
7. Frontend callback page redirects to /dashboard
   ↓
8. Dashboard loads with authenticated session
```

## Error Handling

### Error Handling Strategy

1. **API Errors**: Display user-friendly error messages in UI
2. **Authentication Errors**: Redirect to landing page
3. **Token Refresh Errors**: Redirect to landing page and clear session
4. **Network Errors**: Display retry option to user
5. **Validation Errors**: Show inline validation messages

### Error Display Pattern

```typescript
// Standard error state pattern
const [error, setError] = useState<string | null>(null);

// In UI
{error && (
  <div className="rounded-md bg-red-50 p-4 text-sm text-red-800">
    {error}
  </div>
)}
```

## Environment Configuration

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Configuration Access

```typescript
// All client-side env vars must be prefixed with NEXT_PUBLIC_
const API_URL = process.env.NEXT_PUBLIC_API_URL;
```

## shadcn/ui Component Integration

### Component Selection Rationale

- **Select**: Required for dropdown site selection
- **Button**: Standard clickable actions (login, logout, submit)
- **Card**: Container for analysis results display

### Component Installation

```bash
npx shadcn@latest add select button card
```

### Component Customization

All shadcn components use Tailwind CSS and can be customized via className props:

```typescript
<Button variant="default" size="lg" className="custom-class">
  Sign in with Google
</Button>
```

## Performance Considerations

### Optimization Strategies

1. **Code Splitting**: Next.js App Router automatic code splitting
2. **Server Components**: Use server components where possible (landing page)
3. **Client Components**: Only for interactive components (`'use client'`)
4. **Lazy Loading**: React.lazy() for markdown renderer if needed
5. **Memoization**: React.memo() for expensive components

### Caching Strategy

- **API Responses**: No caching for dynamic analysis data
- **Static Assets**: Next.js automatic static optimization
- **Authentication Tokens**: Managed by browser via httpOnly cookies

## Security Considerations

### Security Measures

1. **httpOnly Cookies**: Access and refresh tokens stored in httpOnly cookies
2. **CORS**: Backend restricts origins to frontend domain
3. **CSRF Protection**: SameSite cookie attribute
4. **XSS Prevention**: React automatic escaping, sanitize markdown if needed
5. **Token Expiration**: Automatic token refresh on 401 responses
6. **Route Protection**: Middleware guards protected routes

### Authentication Security

```typescript
// Tokens are httpOnly - inaccessible to JavaScript
// This prevents XSS attacks from stealing tokens
// All authentication state lives server-side in cookies
```

## Testing Strategy

Testing will focus on component behavior, API integration, and authentication flows using property-based testing where input variation matters, and example-based testing for specific scenarios.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, several redundancies were identified:

- **Redundant**: 4.4 (covered by 4.3 - site rendering)
- **Redundant**: 5.2 (covered by 4.2 - token inclusion in all authenticated requests)
- **Redundant**: 10.2, 10.3 (covered by 5.1 - analysis request parameters)
- **Redundant**: 10.4 (covered by 10.1 - JWT decoding)
- **Combined**: Authentication token inclusion (4.2, 5.2) into single property
- **Combined**: Analysis request parameters (5.1, 10.2, 10.3) into single property
- **Combined**: JWT decoding (10.1, 10.4) into single property

The following properties represent the unique, non-redundant testable behaviors:

### Property 1: Query Parameter Extraction

*For any* valid query parameter in the URL, the callback page SHALL correctly extract and process the parameter value.

**Validates: Requirements 2.5**

### Property 2: Authentication Verification

*For any* cookie state (present, absent, expired, malformed), the dashboard authentication check SHALL correctly determine whether the user is authenticated.

**Validates: Requirements 3.3**

### Property 3: Authenticated Request Token Inclusion

*For any* authenticated API request to any endpoint, the request SHALL include the Access_Token cookie with credentials.

**Validates: Requirements 4.2, 5.2**

### Property 4: Sites List Rendering

*For any* valid sites API response (including empty lists, single site, multiple sites), the Site_Selector SHALL render all returned sites as selectable options.

**Validates: Requirements 4.3, 4.4**

### Property 5: Analysis Request Parameters

*For any* selected site URL, the analysis request SHALL include both the site URL and the authenticated user ID as query parameters.

**Validates: Requirements 5.1, 10.2, 10.3**

### Property 6: Analysis Results Display

*For any* valid analysis API response, the Analysis_Display SHALL render the complete analysis content.

**Validates: Requirements 5.4**

### Property 7: Markdown Rendering

*For any* valid markdown string in the analysis response, the Analysis_Display SHALL correctly render it as formatted HTML.

**Validates: Requirements 5.5**

### Property 8: Token Refresh Trigger

*For any* API endpoint that returns a 401 Unauthorized response, the Token_Manager SHALL automatically attempt to refresh the access token.

**Validates: Requirements 6.1**

### Property 9: Request Retry After Refresh

*For any* API request that failed with 401, after successful token refresh, the original request SHALL be retried with the new access token.

**Validates: Requirements 6.3**

### Property 10: Logout State Cleanup

*For any* authenticated application state, the logout action SHALL clear all authentication-related client-side state.

**Validates: Requirements 9.4**

### Property 11: JWT User ID Extraction

*For any* valid JWT access token, the application SHALL correctly extract the user ID from the `sub` claim in the token payload.

**Validates: Requirements 10.1, 10.4**

## Implementation Notes

### Development Workflow

1. **Setup**: Install dependencies, configure environment variables
2. **shadcn Setup**: Add Select, Button, Card components
3. **API Client**: Implement fetch wrapper with interceptor
4. **Pages**: Build landing, callback, dashboard pages
5. **Components**: Create Site_Selector and Analysis_Display
6. **Middleware**: Add route protection
7. **Testing**: Write property tests and example tests
8. **Styling**: Apply Tailwind CSS for responsive design

### Testing Approach

- **Unit Tests**: Specific component behaviors and edge cases
- **Property Tests**: Universal behaviors across varying inputs (minimum 100 iterations)
- **Integration Tests**: Full authentication and API flows
- **E2E Tests**: User journeys from login to analysis display

Each property test will reference its design property with the tag format:
**Feature: seo-dashboard-frontend, Property {number}: {property_text}**

### Known Limitations

1. **JWT Decoding**: Access tokens in httpOnly cookies cannot be read client-side. Solution: Backend can expose user_id via a separate endpoint or non-httpOnly cookie.
2. **Markdown Security**: User-generated markdown must be sanitized to prevent XSS. Use `react-markdown` with safe defaults.
3. **Loading States**: Long-running analysis requests may appear unresponsive. Consider WebSocket for real-time updates in future iterations.

## Future Enhancements

- **Real-time Updates**: WebSocket connection for streaming analysis results
- **Analysis History**: Display previous analyses for selected sites
- **Multi-site Comparison**: Compare SEO metrics across multiple sites
- **Export Functionality**: Download analysis as PDF or markdown file
- **Caching**: Cache site lists and recent analyses for faster load times
