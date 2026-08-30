import type { Metadata } from "next";
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
    default: "Search Console Agent | AI-Powered SEO Analysis",
    template: "%s | Search Console Agent",
  },
  description:
    "AI-powered weekly SEO recommendations built from your Google Search Console performance data and on-page content. Tailored insights for your business goals.",
  applicationName: "Search Console Agent",
  keywords: ["SEO", "Search Console", "Google", "Analytics", "AI", "SEO Analysis", "Website Optimization"],
  authors: [{ name: "Search Console Agent" }],
  creator: "Search Console Agent",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "any" }
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  manifest: "/site.webmanifest",
  themeColor: "#4f46e5",
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,
  },
  openGraph: {
    type: "website",
    title: "Search Console Agent | AI-Powered SEO Analysis",
    description: "AI-powered weekly SEO recommendations tailored to your business goals",
    siteName: "Search Console Agent",
  },
  twitter: {
    card: "summary_large_image",
    title: "Search Console Agent",
    description: "AI-powered SEO analysis from your Search Console data",
  },
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
