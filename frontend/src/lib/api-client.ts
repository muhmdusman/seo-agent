/**
 * API Client
 *
 * Auth is handled by HttpOnly cookies set by the backend. Browser JavaScript
 * should not read, store, or forward access/refresh tokens.
 */

import { API_BASE_URL } from './config';

type ApiRequestOptions = RequestInit & {
  redirectOnUnauthorized?: boolean;
};

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Make an API request. On 401 the browser is redirected to '/' by default.
   *
   * @param endpoint - API endpoint path (e.g., '/search-console/sites')
   * @param options - Fetch options
   * @returns Promise with typed response data
   */
  async request<T>(
    endpoint: string,
    options: ApiRequestOptions = {},
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const { redirectOnUnauthorized = true, ...fetchOptions } = options;

    const config: RequestInit = {
      cache: 'no-store',
      ...fetchOptions,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (response.status === 401) {
        if (redirectOnUnauthorized && typeof window !== 'undefined') {
          window.location.href = '/';
        }
        throw new Error('Authentication failed');
      }

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === 'string' ? body.detail : `API Error: ${response.status}`);
      }

      return response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        console.error('Network error: Unable to reach the server');
        throw new Error('Unable to connect to server. Please check your connection.');
      }
      throw error;
    }
  }

  /**
   * Convenience method for GET requests
   */
  get<T>(
    endpoint: string,
    options: ApiRequestOptions = {},
  ): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  /**
   * Convenience method for POST requests
   */
  post<T>(
    endpoint: string,
    data?: unknown,
    options: ApiRequestOptions = {},
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
