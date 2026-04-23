"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Play, Pause, RotateCcw, Clock } from "lucide-react";

interface SchedulerStatus {
  running: boolean;
  scan_interval_hours: number;
  next_scan_in: number;
}

export default function SchedulerControl() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/scheduler/status");
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to fetch scheduler status:", err);
    }
  };

  const startScheduler = async () => {
    setLoading(true);
    try {
      await fetch("/api/scheduler/start", { method: "POST" });
      await fetchStatus();
    } catch (err) {
      console.error("Failed to start scheduler:", err);
    } finally {
      setLoading(false);
    }
  };

  const stopScheduler = async () => {
    setLoading(true);
    try {
      await fetch("/api/scheduler/stop", { method: "POST" });
      await fetchStatus();
    } catch (err) {
      console.error("Failed to stop scheduler:", err);
    } finally {
      setLoading(false);
    }
  };

  const triggerScanNow = async () => {
    setLoading(true);
    try {
      await fetch("/api/scheduler/scan-now", { method: "POST" });
    } catch (err) {
      console.error("Failed to trigger scan:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (!status) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-6">
          <RotateCcw className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2">Loading scheduler status...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Autonomous Scheduler
          </CardTitle>
          <CardDescription>
            Continuous security scanning of all monitored repositories
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Status</span>
            <div className="flex items-center gap-2">
              <Badge variant={status.running ? "default" : "secondary"}>
                {status.running ? "Running" : "Stopped"}
              </Badge>
              <Switch
                checked={status.running}
                onCheckedChange={status.running ? stopScheduler : startScheduler}
                disabled={loading}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Scan Interval</span>
            <span className="text-sm text-muted-foreground">
              {status.scan_interval_hours} hours
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Next Scan</span>
            <span className="text-sm text-muted-foreground">
              {status.next_scan_in > 0 ? `${Math.floor(status.next_scan_in / 60)}h ${status.next_scan_in % 60}m` : "Ready"}
            </span>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={triggerScanNow}
              disabled={loading || status.running}
              variant="outline"
              size="sm"
            >
              <Play className="h-4 w-4 mr-2" />
              Scan Now
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
