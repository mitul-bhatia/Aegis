"use client";

import { useEffect, useState } from "react";
import { Bell, BellOff, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ScanInfo } from "@/lib/api";

// ── Notification helpers ──────────────────────────────────

/**
 * Fire a browser push notification for a scan that just reached a terminal state.
 * Does nothing if permission hasn't been granted.
 */
export function notifyScanComplete(scan: ScanInfo) {
  if (typeof window === "undefined") return;
  if (Notification.permission !== "granted") return;

  let title: string;
  let body: string;
  let icon = "/favicon.ico";

  switch (scan.status) {
    case "fixed":
      title = "🛡️ Vulnerability Fixed";
      body = scan.vulnerability_type
        ? `${scan.vulnerability_type} in ${scan.vulnerable_file ?? "unknown file"} — PR ready for review`
        : `Scan #${scan.id} — patch created`;
      break;
    case "awaiting_approval":
      title = "⚠️ Approval Required";
      body = scan.vulnerability_type
        ? `CRITICAL ${scan.vulnerability_type} patched — review required before PR`
        : `Scan #${scan.id} needs your approval`;
      break;
    case "clean":
      title = "✅ Scan Complete — Clean";
      body = `Scan #${scan.id} found no vulnerabilities`;
      break;
    case "false_positive":
      title = "📊 False Positive";
      body = scan.vulnerability_type
        ? `${scan.vulnerability_type} could not be exploited`
        : `Scan #${scan.id} — false positive`;
      break;
    case "failed":
      title = "❌ Scan Failed";
      body = scan.error_message
        ? scan.error_message.slice(0, 100)
        : `Scan #${scan.id} encountered an error`;
      break;
    default:
      return; // Don't notify for intermediate states
  }

  try {
    const notification = new Notification(title, {
      body,
      icon,
      // tag prevents duplicate notifications for the same scan
      tag: `aegis-scan-${scan.id}`,
      // renotify: true means re-show even if same tag already exists
      // (useful if status changes from awaiting_approval → fixed)
    });

    // Clicking the notification focuses the browser window
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  } catch {
    // Notifications can fail silently (e.g., in some iframe contexts)
  }
}

// ── Permission prompt banner ──────────────────────────────

/**
 * A subtle banner that asks the user to enable notifications.
 * Only shows once — dismissed state is saved to localStorage.
 * Renders nothing if permission is already granted or denied.
 */
export function NotificationPermissionBanner() {
  const [show, setShow] = useState(false);
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    // Don't show if:
    // - Notifications not supported
    // - Already granted or denied
    // - User previously dismissed the banner
    if (typeof window === "undefined") return;
    if (!("Notification" in window)) return;
    if (Notification.permission !== "default") return;
    if (localStorage.getItem("aegis_notif_dismissed") === "true") return;

    // Small delay so it doesn't pop up immediately on page load
    const t = setTimeout(() => setShow(true), 2000);
    return () => clearTimeout(t);
  }, []);

  async function handleEnable() {
    setRequesting(true);
    try {
      const result = await Notification.requestPermission();
      if (result === "granted" || result === "denied") {
        setShow(false);
      }
    } finally {
      setRequesting(false);
    }
  }

  function handleDismiss() {
    localStorage.setItem("aegis_notif_dismissed", "true");
    setShow(false);
  }

  if (!show) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-xl border border-border/60 bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm max-w-sm animate-in slide-in-from-bottom-4 duration-300">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15">
        <Bell className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">Enable notifications</p>
        <p className="text-xs text-muted-foreground">
          Get alerted when scans complete or need approval
        </p>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <Button
          size="sm"
          className="h-7 text-xs px-3"
          onClick={handleEnable}
          disabled={requesting}
        >
          {requesting ? "..." : "Enable"}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-foreground"
          onClick={handleDismiss}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

// ── Notification toggle button (for header) ───────────────

/**
 * Small bell icon button for the dashboard header.
 * Shows current permission state and lets user toggle.
 */
export function NotificationToggle() {
  const [permission, setPermission] = useState<NotificationPermission>("default");

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setPermission(Notification.permission);
    }
  }, []);

  async function handleClick() {
    if (!("Notification" in window)) return;

    if (permission === "default") {
      const result = await Notification.requestPermission();
      setPermission(result);
    }
    // If already granted/denied, clicking just shows current state (can't revoke via JS)
  }

  if (!("Notification" in (typeof window !== "undefined" ? window : {}))) return null;

  const isGranted = permission === "granted";
  const isDenied = permission === "denied";

  return (
    <Button
      variant="ghost"
      size="icon"
      className={`h-8 w-8 ${
        isGranted ? "text-primary" : isDenied ? "text-muted-foreground/40" : "text-muted-foreground"
      }`}
      onClick={handleClick}
      title={
        isGranted ? "Notifications enabled"
        : isDenied ? "Notifications blocked — change in browser settings"
        : "Enable notifications"
      }
    >
      {isGranted ? (
        <Bell className="h-4 w-4" />
      ) : (
        <BellOff className="h-4 w-4" />
      )}
    </Button>
  );
}
