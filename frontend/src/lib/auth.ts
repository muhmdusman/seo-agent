import { API_BASE_URL } from './config';

// Fetch the authenticated user's id from the backend (cookies are httpOnly)
export async function getCurrentUserId(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, { credentials: 'include' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.user_id ?? null;
  } catch {
    return null;
  }
}

// Log out: clear cookies on backend, then redirect to landing
export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
  } catch {
    // ignore
  } finally {
    window.location.href = '/';
  }
}
