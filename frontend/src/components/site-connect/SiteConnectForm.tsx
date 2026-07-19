"use client";

import { FormEvent, useState } from "react";

import { getGoogleLoginUrl } from "@/lib/api/auth";
import { saveSiteUrl } from "@/lib/storage";
import { normalizeWebsiteUrl } from "@/lib/validators";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function SiteConnectForm() {
  const [siteUrl, setSiteUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalized = normalizeWebsiteUrl(siteUrl);
    if (!normalized) {
      setError("Enter a valid website URL, e.g. example.com");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    // Persist the site URL so we can read it back after the
    // full-page OAuth redirect completes.
    saveSiteUrl(normalized);

    window.location.href = getGoogleLoginUrl();
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-4">
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          type="text"
          inputMode="url"
          placeholder="yourwebsite.com"
          value={siteUrl}
          onChange={(event) => setSiteUrl(event.target.value)}
          error={error}
          aria-label="Website URL"
          autoFocus
        />
        <Button type="submit" isLoading={isSubmitting}>
          Connect with Google
        </Button>
      </div>
      <p className="text-xs text-zinc-500">
        We&apos;ll ask for read-only access to Google Search Console so we
        can pull data for this site.
      </p>
    </form>
  );
}
