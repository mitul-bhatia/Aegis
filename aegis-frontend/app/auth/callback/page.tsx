"use client";

import { useEffect, useState, Suspense, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Shield, Loader2 } from "lucide-react";

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState("Authenticating with GitHub...");
  const [error, setError] = useState("");
  // Guard against double-invocation (React StrictMode / fast refresh)
  const didRun = useRef(false);

  useEffect(() => {
    if (didRun.current) return;
    didRun.current = true;

    const code = searchParams.get("code");
    if (!code) {
      setError("No authorization code received from GitHub.");
      return;
    }

    // Prevent re-using the same code if the component re-mounts
    const usedKey = `oauth_used_${code}`;
    if (sessionStorage.getItem(usedKey)) {
      // Code already consumed — redirect to login
      router.replace("/");
      return;
    }
    sessionStorage.setItem(usedKey, "1");

    async function authenticate() {
      try {
        setStatus("Exchanging token...");

        const user = await api.exchangeGitHubCode(code!);

        localStorage.setItem("aegis_user_id", String(user.id));
        localStorage.setItem("aegis_username", user.github_username);
        localStorage.setItem("aegis_avatar", user.github_avatar_url);

        setStatus(`Welcome, ${user.github_username}! Redirecting...`);
        setTimeout(() => router.push("/dashboard"), 1000);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(`Authentication failed: ${msg}`);
        console.error("Auth error:", err);
      }
    }

    authenticate();
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <Shield className="mx-auto mb-6 h-12 w-12 text-primary" />
        {error ? (
          <div>
            <p className="text-destructive font-semibold">{error}</p>
            <Link href="/" className="mt-4 inline-block text-sm text-primary underline">
              Go back
            </Link>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <p className="text-muted-foreground">{status}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AuthCallback() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
