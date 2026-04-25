"use client";

import React from "react";
import { Shield, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: React.ReactNode;
  /** Optional title shown in the fallback UI */
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary — catches any render error in its children and shows a
 * friendly fallback instead of crashing the whole page.
 *
 * Usage:
 *   <ErrorBoundary fallbackTitle="Failed to load scan details">
 *     <SomeComponent />
 *   </ErrorBoundary>
 *
 * Clicking "Retry" resets the error state so React re-renders the children.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  // Called by React when a child throws during render
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  // Log the error (could send to Sentry etc. in production)
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary] caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-xl border border-red-500/30 bg-red-950/10 p-6 text-center">
          <Shield className="mx-auto h-8 w-8 text-red-400 mb-3" />
          <p className="font-semibold text-red-300 mb-1">
            {this.props.fallbackTitle ?? "Something went wrong"}
          </p>
          {this.state.error?.message && (
            <p className="text-xs text-zinc-500 mb-3 font-mono">
              {this.state.error.message}
            </p>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Retry
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
