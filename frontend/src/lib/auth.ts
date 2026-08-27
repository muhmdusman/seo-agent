import { apiClient } from './api-client';

// Fetch the authenticated user's id from the backend using Bearer token
export async function getCurrentUserId(): Promise<string | null> {
  try {
    const data = await apiClient.get<{ user_id: string }>('/auth/me');
    return data.user_id ?? null;
  } catch {
    return null;
  }
}

// Log out: clear tokens from localStorage and redirect to landing
export async function logout(): Promise<void> {
  try {
    // Clear tokens from localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    
    // Try to call logout endpoint (optional, since tokens are client-side)
    await apiClient.post('/auth/logout');
  } catch {
    // ignore
  } finally {
    window.location.href = '/';
  }
}
