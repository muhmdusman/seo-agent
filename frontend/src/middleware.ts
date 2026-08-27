import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js middleware for route protection based on authentication state.
 *
 * Note: Middleware runs on the server, so it can't access localStorage.
 * We'll handle auth checks client-side for now.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow callback page always (it handles token storage)
  if (pathname.startsWith('/callback')) {
    return NextResponse.next();
  }

  // For dashboard, we'll let the client-side check handle it
  // since tokens are now in localStorage (not cookies)
  return NextResponse.next();
}

/**
 * Configure which routes the middleware should run on.
 */
export const config = {
  matcher: ['/', '/dashboard/:path*', '/callback'],
};
