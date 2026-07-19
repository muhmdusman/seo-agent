import { API_BASE_URL } from "@/lib/config";

/**
 * Builds the URL that kicks off the Google OAuth flow on the backend.
 * Navigating the browser to this URL redirects to Google's consent screen.
 */
export function getGoogleLoginUrl(): string {
  return `${API_BASE_URL}/auth/google`;
}
