"use client";

import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearSiteUrl, getSiteUrl } from "@/lib/storage";
import { Button } from "@/components/ui/button";

export function CallbackStatus() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const status = searchParams.get("status");
  const accessToken = searchParams.get("access_token");
  const refreshToken = searchParams.get("refresh_token");
  const email = searchParams.get("email");

  const [siteUrl, setSiteUrl] = useState<string | null>(null);

  useEffect(() => {
    setSiteUrl(getSiteUrl());
    return () => clearSiteUrl();
  }, []);

  useEffect(() => {
    if (status === "success" && accessToken && refreshToken) {
      console.log("🔐 Storing tokens in localStorage");
      console.log("Access token length:", accessToken.length);
      console.log("Refresh token length:", refreshToken.length);
      console.log("Access token preview:", accessToken.substring(0, 50) + "...");
      
      // Store tokens in localStorage
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      
      console.log("✅ Tokens stored, redirecting to dashboard");
      
      // Redirect to dashboard
      router.push("/dashboard");
    } else {
      console.log("❌ Missing tokens or status");
      console.log("Status:", status);
      console.log("Has access token:", !!accessToken);
      console.log("Has refresh token:", !!refreshToken);
    }
  }, [status, accessToken, refreshToken, router]);

  if (status === "success") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex flex-col items-center gap-4"
      >
        <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-indigo-600" />
        <p className="text-sm text-slate-600">
          Connected. Redirecting to your dashboard...
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        aria-hidden="true"
        className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 ring-1 ring-red-200"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
          <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
        </svg>
      </div>
      <h1 className="text-xl font-semibold text-slate-900">
        Something went wrong
      </h1>
      <p className="text-sm leading-relaxed text-slate-600">
        We couldn&apos;t connect your Google account. Please try again.
      </p>
      <Link href="/" className="mt-2 w-full sm:w-auto">
        <Button variant="secondary" className="w-full sm:w-auto">
          Back to home
        </Button>
      </Link>
    </div>
  );
}
