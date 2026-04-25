"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Shield, Loader2 } from "lucide-react";
import { Suspense } from "react";

function SuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const userId = searchParams.get("user_id");
    const username = searchParams.get("username");
    const avatar = searchParams.get("avatar");

    if (userId && username) {
      // Store user info in localStorage
      localStorage.setItem("aegis_user_id", userId);
      localStorage.setItem("aegis_username", username);
      if (avatar) {
        localStorage.setItem("aegis_avatar", avatar);
      }

      // Redirect to dashboard
      setTimeout(() => router.push("/dashboard"), 1000);
    } else {
      // Redirect to home with error
      setTimeout(() => router.push("/?error=missing_user_data"), 1000);
    }
  }, [searchParams, router]);

  const username = searchParams.get("username");

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <Shield className="mx-auto mb-6 h-12 w-12 text-primary" />
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <p className="text-muted-foreground">
            Welcome, {username}! Redirecting to dashboard...
          </p>
        </div>
      </div>
    </div>
  );
}

export default function AuthSuccess() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <SuccessContent />
    </Suspense>
  );
}