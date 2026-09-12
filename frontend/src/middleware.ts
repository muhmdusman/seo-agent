import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js middleware for route protection based on authentication state.
 *
 * The backend owns auth cookies, so route-level checks happen client-side
 * through /auth/me for now.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow callback page always (it handles token storage)
  if (pathname.startsWith('/callback')) {
    return NextResponse.next();
  }

  // For dashboard, we'll let the client-side check handle it.
  return NextResponse.next();
}

/**
 * Configure which routes the middleware should run on.
 */
export const config = {
  matcher: ['/', '/dashboard/:path*', '/callback'],
};
