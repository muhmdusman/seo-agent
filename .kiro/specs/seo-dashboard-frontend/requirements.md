# Requirements Document

## Introduction

The SEO Dashboard Frontend is a Next.js web application that authenticates users via Google OAuth 2.0, displays their Google Search Console sites, and presents complete SEO analysis results from the backend agent. The application implements a minimal user interface using TypeScript, Tailwind CSS, and shadcn/ui components, with automatic token refresh for expired sessions.

## Glossary

- **Frontend_Application**: The Next.js web application that provides the user interface for the SEO Dashboard
- **Landing_Page**: The initial page that presents the Google login option to unauthenticated users
- **Callback_Page**: The page that receives OAuth redirect after successful Google authentication
- **Dashboard_Page**: The main authenticated page that displays sites dropdown and analysis results
- **Authentication_Service**: The client-side service that manages OAuth flow and session tokens
- **Site_Selector**: The dropdown component that displays available Google Search Console sites
- **Analysis_Display**: The component that presents complete SEO analysis results from the backend agent
- **Token_Manager**: The service that handles access token refresh when tokens expire
- **Backend_API**: The FastAPI service at `/api/v1` that provides authentication and data endpoints
- **Access_Token**: The JWT token stored in httpOnly cookie for authenticating API requests
- **Refresh_Token**: The long-lived token stored in httpOnly cookie for obtaining new access tokens
- **SEO_Analysis**: The complete analysis output from the backend weekly agent for a selected site

## Requirements

### Requirement 1

**User Story:** As an unauthenticated user, I want to see a landing page with a Google login button, so that I can authenticate and access the dashboard

#### Acceptance Criteria

1. THE Frontend_Application SHALL display the Landing_Page at the root path `/`
2. THE Landing_Page SHALL render a button labeled "Sign in with Google"
3. WHEN the user clicks the login button, THE Frontend_Application SHALL redirect to `/api/v1/auth/google`
4. THE Landing_Page SHALL use Tailwind CSS for styling
5. THE Landing_Page SHALL display a title "SEO Dashboard" above the login button

### Requirement 2

**User Story:** As a user completing OAuth authentication, I want to be redirected to a callback page that processes the authentication result, so that I can access the dashboard after successful login

#### Acceptance Criteria

1. THE Frontend_Application SHALL display the Callback_Page at path `/callback`
2. WHEN the Callback_Page receives a query parameter `status=success`, THE Frontend_Application SHALL redirect to `/dashboard`
3. WHEN the Callback_Page receives a query parameter `status=error`, THE Frontend_Application SHALL redirect to `/` with an error message displayed
4. WHILE the Callback_Page is processing the authentication result, THE Frontend_Application SHALL display a loading indicator
5. THE Callback_Page SHALL extract the `status` parameter from the URL query string

### Requirement 3

**User Story:** As an authenticated user, I want to access a protected dashboard page, so that I can view my sites and analysis results

#### Acceptance Criteria

1. THE Frontend_Application SHALL display the Dashboard_Page at path `/dashboard`
2. WHEN an unauthenticated user attempts to access `/dashboard`, THE Frontend_Application SHALL redirect to `/`
3. THE Dashboard_Page SHALL verify authentication by checking for the presence of the Access_Token cookie
4. THE Dashboard_Page SHALL use TypeScript for type safety
5. THE Dashboard_Page SHALL apply Tailwind CSS for layout and styling

### Requirement 4

**User Story:** As an authenticated user on the dashboard, I want to see a dropdown of my Google Search Console sites, so that I can select which site to analyze

#### Acceptance Criteria

1. WHEN the Dashboard_Page loads, THE Frontend_Application SHALL request the user's sites from `/api/v1/search-console/sites`
2. THE Frontend_Application SHALL include the Access_Token cookie in the sites request
3. WHEN the sites request succeeds, THE Frontend_Application SHALL render the Site_Selector dropdown with the retrieved sites
4. THE Site_Selector SHALL display each site URL as a selectable option
5. WHEN the sites request fails, THE Frontend_Application SHALL display an error message to the user
6. THE Site_Selector SHALL use a shadcn/ui Select component

### Requirement 5

**User Story:** As an authenticated user, I want to select a site from the dropdown and receive the complete analysis, so that I can review SEO improvements for that site

#### Acceptance Criteria

1. WHEN the user selects a site from the Site_Selector, THE Frontend_Application SHALL request analysis from `/api/v1/agent/weekly` with the selected site URL and user ID
2. THE Frontend_Application SHALL include the Access_Token cookie in the analysis request
3. WHILE the analysis request is pending, THE Frontend_Application SHALL display a loading indicator with the text "Analyzing..."
4. WHEN the analysis completes, THE Frontend_Application SHALL render the Analysis_Display with the complete results
5. THE Analysis_Display SHALL render the analysis text as formatted markdown
6. THE Frontend_Application SHALL wait for the complete analysis response before displaying results
7. IF the analysis request fails, THEN THE Frontend_Application SHALL display an error message to the user

### Requirement 6

**User Story:** As an authenticated user with an expired access token, I want the application to automatically refresh my session, so that I can continue using the dashboard without interruption

#### Acceptance Criteria

1. WHEN an API request returns a 401 Unauthorized response, THE Token_Manager SHALL request a new Access_Token from `/api/v1/auth/refresh`
2. THE Token_Manager SHALL include the Refresh_Token cookie in the refresh request
3. WHEN the token refresh succeeds, THE Token_Manager SHALL retry the original failed API request with the new Access_Token
4. WHEN the token refresh fails, THE Frontend_Application SHALL redirect the user to `/`
5. THE Token_Manager SHALL handle token refresh transparently without user interaction
6. IF the Refresh_Token is missing or invalid, THEN THE Frontend_Application SHALL redirect to `/`

### Requirement 7

**User Story:** As a user, I want the application to use minimal shadcn/ui components, so that the interface remains simple and lightweight

#### Acceptance Criteria

1. THE Frontend_Application SHALL use shadcn/ui Select component for the Site_Selector
2. THE Frontend_Application SHALL use shadcn/ui Button component for clickable actions
3. THE Frontend_Application SHALL use shadcn/ui Card component for the Analysis_Display container
4. THE Frontend_Application SHALL limit shadcn/ui component usage to Select, Button, and Card only
5. THE Frontend_Application SHALL implement custom loading indicators using Tailwind CSS

### Requirement 8

**User Story:** As a developer, I want the application built with Next.js 14+ using TypeScript and the App Router, so that the codebase follows modern React patterns

#### Acceptance Criteria

1. THE Frontend_Application SHALL use Next.js version 14 or higher
2. THE Frontend_Application SHALL use the Next.js App Router for routing
3. THE Frontend_Application SHALL use TypeScript for all source files
4. THE Frontend_Application SHALL define TypeScript interfaces for API response types
5. THE Frontend_Application SHALL use Tailwind CSS for all styling
6. THE Frontend_Application SHALL store API base URL in environment variable `NEXT_PUBLIC_API_URL`

### Requirement 9

**User Story:** As a user, I want a logout option on the dashboard, so that I can end my session securely

#### Acceptance Criteria

1. THE Dashboard_Page SHALL display a logout button in the page header
2. WHEN the user clicks the logout button, THE Frontend_Application SHALL request `/api/v1/auth/logout`
3. WHEN the logout request completes, THE Frontend_Application SHALL redirect to `/`
4. THE Frontend_Application SHALL clear client-side authentication state on logout
5. THE logout button SHALL use a shadcn/ui Button component

### Requirement 10

**User Story:** As an authenticated user, I want the analysis request to include proper authentication, so that the backend can identify my account and access my Google Search Console data

#### Acceptance Criteria

1. THE Frontend_Application SHALL extract the user ID from the Access_Token JWT payload
2. WHEN requesting analysis, THE Frontend_Application SHALL include the user ID as a query parameter
3. WHEN requesting analysis, THE Frontend_Application SHALL include the selected site URL as a query parameter
4. THE Frontend_Application SHALL decode the Access_Token to extract the `sub` claim as the user ID
5. IF the Access_Token cannot be decoded, THEN THE Frontend_Application SHALL redirect to `/`
