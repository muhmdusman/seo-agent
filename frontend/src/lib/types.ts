// API Response Types for SEO Dashboard Frontend

/**
 * Represents a Google Search Console site
 */
export interface Site {
  siteUrl: string;
  permissionLevel: string;
}

/**
 * Response from the sites API endpoint (Google Search Console raw shape)
 */
export interface SitesResponse {
  siteEntry?: Site[];
}

/**
 * Response from the analysis API endpoint
 */
export interface AnalysisResponse {
  analysis: string;
  site_url: string;
  generated_at: string;
}

/**
 * JWT Access Token payload structure
 */
export interface AuthTokenPayload {
  sub: string; // user_id
  exp: number; // expiration timestamp
  iat: number; // issued at timestamp
}

/**
 * Standard error response from API
 */
export interface ErrorResponse {
  detail: string;
}
