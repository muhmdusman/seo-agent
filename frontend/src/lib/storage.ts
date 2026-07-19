const SITE_URL_KEY = "sca_site_url";

/**
 * The OAuth flow involves a full-page redirect to Google and back, so any
 * in-memory React state would be lost. We stash the site URL the user
 * entered in sessionStorage before redirecting, and read it back once the
 * flow completes.
 */
export function saveSiteUrl(url: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(SITE_URL_KEY, url);
}

export function getSiteUrl(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(SITE_URL_KEY);
}

export function clearSiteUrl(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(SITE_URL_KEY);
}
