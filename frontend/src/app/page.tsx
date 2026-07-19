import { SiteConnectForm } from "@/components/site-connect/SiteConnectForm";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 px-6 py-16">
      <main className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-sm ring-1 ring-zinc-200 sm:p-10">
        <div className="mb-8 flex flex-col gap-2 text-center">
          <h1 className="text-2xl font-semibold text-zinc-900">
            Search Console Agent
          </h1>
          <p className="text-sm text-zinc-500">
            Enter your website to connect it with Google Search Console
            and start pulling search analytics.
          </p>
        </div>

        <SiteConnectForm />
      </main>
    </div>
  );
}
