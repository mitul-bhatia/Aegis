import type { Metadata } from "next";
import { Syne, Share_Tech_Mono, DM_Sans } from "next/font/google";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThreatBanner } from "@/components/ThreatBanner";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  display: "swap",
});

const shareTechMono = Share_Tech_Mono({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-share-tech-mono",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Aegis — Autonomous Security Remediation",
  description:
    "Four AI agents — Finder, Exploiter, Engineer, Verifier — detect, prove, patch, and verify every vulnerability in your GitHub repositories. Automatically.",
  keywords: ["security", "AI", "vulnerability", "remediation", "GitHub", "autonomous"],
  openGraph: {
    title: "Aegis — Autonomous Security Remediation",
    description: "Four AI agents that detect, prove, patch, and verify every vulnerability. Automatically.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${dmSans.variable} ${syne.variable} ${shareTechMono.variable} font-sans antialiased min-h-screen`}
        style={{ background: "var(--background)", color: "var(--foreground)" }}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange={false}
        >
          <ThreatBanner />
          <div className="min-h-screen">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  );
}
