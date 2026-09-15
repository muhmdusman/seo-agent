import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Search Console Agent | SEO review & fixes",
    template: "%s | Search Console Agent",
  },
  description:
    "AI-powered weekly SEO recommendations built from your Google Search Console performance data and on-page content. Tailored insights for your business goals.",
  applicationName: "Search Console Agent",
  keywords: ["SEO", "Search Console", "Google", "Analytics", "AI", "SEO review", "Website Optimization"],
  authors: [{ name: "Search Console Agent" }],
  creator: "Search Console Agent",
  icons: {
    icon: [
      { url: "/favicon/favicon.ico", sizes: "any" },
      { url: "/favicon/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon/favicon-16x16.png", sizes: "16x16", type: "image/png" },
    ],
    apple: [{ url: "/favicon/apple-icon-180x180.png", sizes: "180x180" }],
  },
  manifest: "/favicon/manifest.json",
  openGraph: {
    type: "website",
    title: "Search Console Agent | SEO review & fixes",
    description: "AI-powered weekly SEO recommendations tailored to your business goals",
    siteName: "Search Console Agent",
  },
  twitter: {
    card: "summary_large_image",
    title: "Search Console Agent",
    description: "Evidence-backed SEO reviews, fixes and visibility opportunities from your Search Console data",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#f8eee4",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="app-aurora flex min-h-full flex-col">{children}</body>
    </html>
  );
}
