"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { clearSiteUrl, getSiteUrl } from "@/lib/storage";
import { Button } from "@/components/ui/button";

export function CallbackStatus() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");
  const email = searchParams.get("email");

  const [siteUrl, setSiteUrl] = useState<string | null>(null);

  useEffect(() => {
    setSiteUrl(getSiteUrl());
    return () => clearSiteUrl();
  }, []);

  useEffect(() => {
    if (status === "success") {
      window.location.href = "/dashboard";
    }
  }, [status]);

  if (status === "success") {
    return (
      <div className="flex flex-col items-center gap-3">
        <p className="text-sm text-zinc-500">Redirecting to your dashboard...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
        ✕
      </div>
      <h1 className="text-xl font-semibold text-zinc-900">
        Something went wrong
      </h1>
      <p className="text-sm text-zinc-500">
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
