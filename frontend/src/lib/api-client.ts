/**
 * API Client
 *
 * Wraps the fetch API for the backend. All requests include credentials so the
 * httpOnly `access_token` / `refresh_token` cookies are sent automatically.
 *
 * The backend refreshes tokens server-side inside its auth dependency, so there
 * is no client-side refresh flow. A 401 means the user is fully unauthenticated,
 * in which case we redirect back to the landing page.
 */

import { API_BASE_URL } from './config';

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Make an API request. On 401 the browser is redirected to '/'.
   *
   * @param endpoint - API endpoint path (e.g., '/search-console/sites')
   * @param options - Fetch options
   * @returns Promise with typed response data
   */
  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      ...options,
      credentials: 'include', // Include httpOnly auth cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    const response = await fetch(url, config);

    // 401 means fully unauthenticated - redirect to landing page
    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        window.location.href = '/';
      }
      throw new Error('Authentication failed');
    }

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Convenience method for GET requests
   */
  get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * Convenience method for POST requests
   */
  post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
