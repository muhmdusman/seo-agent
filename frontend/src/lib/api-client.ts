/**
 * API Client
 *
 * Wraps the fetch API for the backend. All requests include the access_token
 * from localStorage in the Authorization header.
 *
 * On 401, we try to refresh the token. If refresh fails, redirect to login.
 */

import { API_BASE_URL } from './config';

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Get access token from localStorage
   */
  private getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    const token = localStorage.getItem('access_token');
    if (token) {
      console.log("🔑 Using access token from localStorage");
      console.log("Token length:", token.length);
      console.log("Token preview:", token.substring(0, 50) + "...");
    } else {
      console.log("⚠️  No access token in localStorage");
    }
    return token;
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
    const token = this.getAccessToken();
    
    const config: RequestInit = {
      ...options,
      credentials: 'include', // Still include for potential cookie-based refresh
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
    };

    const response = await fetch(url, config);

    // 401 means fully unauthenticated - clear tokens and redirect to landing page
    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
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
