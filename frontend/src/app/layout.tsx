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
    default: "Search Console Agent",
    template: "%s | Search Console Agent",
  },
  description:
    "Weekly SEO recommendations built from your Google Search Console performance data and on-page content.",
  applicationName: "Search Console Agent",
  // Next serves app/icon.svg from this entry; declaring the type keeps the
  // markup explicit rather than relying on extension sniffing.
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
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
