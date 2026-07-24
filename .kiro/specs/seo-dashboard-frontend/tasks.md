# Implementation Plan: SEO Dashboard Frontend

## Overview

This implementation plan breaks down the SEO Dashboard Frontend into discrete coding tasks. The application is built with Next.js 14+ using TypeScript, the App Router, Tailwind CSS, and minimal shadcn/ui components. The implementation follows a progressive approach: setup and infrastructure first, then core authentication and API integration, followed by page implementations, and finally component implementations.

## Tasks

- [ ] 1. Setup shadcn/ui and install required components
  - Install shadcn/ui CLI and initialize configuration
  - Add Select, Button, and Card components using `npx shadcn@latest add select button card`
  - Verify components are installed in `src/components/ui/` directory
  - Configure Tailwind CSS to work with shadcn components
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.5_

- [ ] 2. Create TypeScript type definitions
  - Define `Site`, `SitesResponse`, `AnalysisResponse`, `AuthTokenPayload`, and `ErrorResponse` interfaces
  - Create `src/lib/types.ts` file with all API response types
  - Export all types for use across the application
  - _Requirements: 8.4_

- [ ] 3. Implement Token Manager service
  - Create `src/lib/token-manager.ts` with `TokenManager` class
  - Implement `refresh()` method that calls `/api/v1/auth/refresh`
  - Add concurrent refresh request prevention logic
  - Include credentials in refresh requests for Refresh_Token cookie
  - _Requirements: 6.1, 6.2, 6.5, 6.6_

- [ ] 4. Implement API client with token refresh interceptor
  - Create `src/lib/api-client.ts` with `ApiClient` class
  - Implement `request()` method with fetch wrapper
  - Add 401 response detection and automatic refresh retry logic
  - Implement `get()` and `post()` convenience methods
  - Include credentials in all API requests for Access_Token cookie
  - Use `NEXT_PUBLIC_API_URL` environment variable for base URL
  - _Requirements: 4.2, 5.2, 6.1, 6.3, 6.4, 8.6_

- [ ] 5. Create authentication helper functions
  - Create `src/lib/auth.ts` with `getUserIdFromToken()` function
  - Implement JWT decoding to extract user ID from `sub` claim
  - Add `getAccessTokenFromCookie()` helper function
  - Implement `logout()` function that calls `/api/v1/auth/logout` and redirects to `/`
  - _Requirements: 9.2, 9.3, 9.4, 10.1, 10.4_

- [ ] 6. Create Next.js middleware for route protection
  - Create `src/middleware.ts` file
  - Implement authentication check using Access_Token cookie
  - Redirect unauthenticated users from `/dashboard` to `/`
  - Redirect authenticated users from `/` to `/dashboard`
  - Configure matcher for `/` and `/dashboard/:path*` routes
  - _Requirements: 3.2, 3.3_

- [ ] 7. Create Landing Page component
  - Create `src/app/page.tsx` file
  - Render "Welcome to our SEO Tool" title and "Please Authorize with Google" button
  - Implement button click handler that redirects to `/api/v1/auth/google`
  - Use shadcn/ui Button component for login button
  - Apply Tailwind CSS for layout and styling
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.2_

- [ ] 8. Create Callback Page component
  - Create `src/app/callback/page.tsx` file
  - Extract `status` query parameter from URL
  - Redirect to `/dashboard` when `status=success`
  - Redirect to `/` with error message when `status=error`
  - Display loading indicator during processing
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 9. Create Loading Spinner component
  - Create `src/components/loading-spinner.tsx` file
  - Implement spinner using Tailwind CSS animations
  - Accept optional `text` prop for custom loading message
  - Use Tailwind CSS for styling (no shadcn component)
  - _Requirements: 7.5_

- [ ] 10. Create Site Selector component
  - Create `src/components/site-selector.tsx` file as client component
  - Fetch sites from `/api/v1/search-console/sites` on mount
  - Render shadcn/ui Select component with fetched sites
  - Display each site URL as a selectable option
  - Handle loading and error states
  - Accept `onSiteSelect` callback prop
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 7.1_

- [ ] 11. Create Analysis Display component
  - Create `src/components/analysis-display.tsx` file as client component
  - Accept `siteUrl` and `analysis` props
  - Render shadcn/ui Card component with CardHeader and CardContent
  - Install and use `react-markdown` for markdown rendering
  - Display site URL in card title
  - Apply Tailwind prose classes for markdown styling
  - _Requirements: 5.4, 5.5, 7.3_

- [ ] 12. Create Dashboard Page component
  - Create `src/app/dashboard/page.tsx` file as client component
  - Extract user ID from JWT token on mount using `getUserIdFromToken()`
  - Implement `handleSiteSelect()` function that requests analysis from `/api/v1/agent/weekly`
  - Include user ID and site URL as query parameters in analysis request
  - Manage loading, error, and success states for site selection and analysis
  - Render logout button in header using shadcn/ui Button
  - Render Site_Selector component
  - Render Analysis_Display component when analysis is available
  - Display loading indicator during analysis with "Analyzing..." text
  - Display error messages when requests fail
  - Apply Tailwind CSS for layout and styling
  - _Requirements: 3.1, 3.4, 3.5, 5.1, 5.2, 5.3, 5.4, 5.6, 5.7, 9.1, 9.5, 10.2, 10.3, 10.5_

- [ ] 13. Update or create root layout
  - Update `src/app/layout.tsx` with proper HTML structure
  - Add application metadata (title, description)
  - Include Tailwind CSS imports
  - Configure font settings if needed
  - _Requirements: 8.1, 8.2, 8.5_

- [ ] 14. Create environment configuration
  - Create `.env.local` file with `NEXT_PUBLIC_API_URL` variable
  - Document required environment variables in README
  - Set default value to `http://localhost:8000`
  - _Requirements: 8.6_

## Notes

- Each task references specific requirements for traceability
- The implementation uses TypeScript throughout for type safety
- All styling uses Tailwind CSS v4
- Only three shadcn/ui components are used: Select, Button, and Card
- API client automatically handles token refresh on 401 responses
- Authentication state is managed via httpOnly cookies set by the backend
- The App Router pattern is used for all pages and routes

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1"]
    },
    {
      "id": 1,
      "tasks": ["2", "5", "9"]
    },
    {
      "id": 2,
      "tasks": ["3", "6"]
    },
    {
      "id": 3,
      "tasks": ["4", "7"]
    },
    {
      "id": 4,
      "tasks": ["8", "10"]
    },
    {
      "id": 5,
      "tasks": ["11", "13", "14"]
    },
    {
      "id": 6,
      "tasks": ["12"]
    }
  ]
}
```
