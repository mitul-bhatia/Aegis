import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Aegis — Autonomous Security Remediation",
  description:
    "AI-powered vulnerability detection, exploitation, and patching for your GitHub repositories.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="antialiased min-h-screen bg-background">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
