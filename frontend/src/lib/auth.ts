import { apiClient } from './api-client';

type GetCurrentUserOptions = {
  redirectOnUnauthorized?: boolean;
};

// Fetch the authenticated user's id from the backend using HttpOnly cookies.
export async function getCurrentUserId(
  options: GetCurrentUserOptions = {},
): Promise<string | null> {
  try {
    const data = await apiClient.get<{ user_id: string }>('/auth/me', options);
    return data.user_id ?? null;
  } catch {
    return null;
  }
}

// Log out: clear server-owned auth cookies and redirect to landing.
export async function logout(): Promise<void> {
  try {
    await apiClient.post('/auth/logout', undefined, {
      redirectOnUnauthorized: false,
    });
  } catch {
    // ignore
  } finally {
    window.location.href = '/';
  }
}
