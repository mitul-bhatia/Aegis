"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { api, type AnalyticsData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Shield, ArrowLeft, TrendingUp, Clock, CheckCircle2,
  AlertTriangle, Loader2, BarChart2, RefreshCw,
} from "lucide-react";

// ── Colour palette ────────────────────────────────────────
const SEVERITY_COLOURS: Record<string, string> = {
  CRITICAL: "#ef4444",
  ERROR:    "#ef4444",
  HIGH:     "#f97316",
  WARNING:  "#f59e0b",
  MEDIUM:   "#f59e0b",
  LOW:      "#3b82f6",
};

const CHART_COLOURS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];

// ── Stat card ─────────────────────────────────────────────
function StatCard({
  label, value, sub, icon: Icon, colour,
}: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; colour: string;
}) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
        <Icon className={`h-4 w-4 ${colour}`} />
      </div>
      <p className={`text-2xl font-bold ${colour}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

// ── Custom tooltip ────────────────────────────────────────
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border/50 bg-card/95 px-3 py-2 text-xs shadow-xl backdrop-blur-sm">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────
export default function AnalyticsPage() {
  const router = useRouter();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState(0);
  const [days, setDays] = useState(30);

  useEffect(() => {
    api.getMe().then((user) => {
      if (!user) { router.push("/"); return; }
      setUserId(user.id);
    });
  }, [router]);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    api.getAnalytics(userId, days)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userId, days]);

  // Build severity pie data
  const severityPieData = data
    ? Object.entries(data.severity_dist).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
                <ArrowLeft className="h-4 w-4" />
                Dashboard
              </Button>
            </Link>
            <div className="h-4 w-px bg-border" />
            <Shield className="h-5 w-5 text-primary" />
            <span className="font-semibold text-sm">Security Analytics</span>
          </div>

          {/* Period selector */}
          <div className="flex items-center gap-2">
            {[7, 30, 90].map((d) => (
              <Button
                key={d}
                size="sm"
                variant={days === d ? "default" : "outline"}
                className="h-7 text-xs"
                onClick={() => setDays(d)}
              >
                {d}d
              </Button>
            ))}
            <Button
              variant="ghost" size="icon"
              className="h-7 w-7"
              onClick={() => { setLoading(true); api.getAnalytics(userId, days).then(setData).finally(() => setLoading(false)); }}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {loading ? (
          <div className="flex items-center justify-center py-32">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !data ? (
          <div className="flex flex-col items-center justify-center py-32 gap-3">
            <BarChart2 className="h-10 w-10 text-muted-foreground/30" />
            <p className="text-muted-foreground">No analytics data available yet</p>
          </div>
        ) : (
          <>
            {/* ── KPI row ── */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard
                label="Total Scans"
                value={data.total_scans}
                sub={`last ${data.period_days} days`}
                icon={Shield}
                colour="text-primary"
              />
              <StatCard
                label="Vulns Fixed"
                value={data.total_fixed}
                sub={`${Math.round(data.fix_rate * 100)}% fix rate`}
                icon={CheckCircle2}
                colour="text-emerald-400"
              />
              <StatCard
                label="Avg Time to Fix"
                value={data.mttr_hours > 0 ? `${data.mttr_hours}h` : "—"}
                sub="mean time to remediation"
                icon={Clock}
                colour="text-amber-400"
              />
              <StatCard
                label="Regressions"
                value={data.regressions}
                sub="previously fixed vulns that reappeared"
                icon={AlertTriangle}
                colour={data.regressions > 0 ? "text-red-400" : "text-muted-foreground"}
              />
            </div>

            {/* ── Vulnerability trend chart ── */}
            <div className="rounded-xl border border-border/50 bg-card/60 p-6 backdrop-blur-sm">
              <div className="flex items-center gap-2 mb-6">
                <TrendingUp className="h-4 w-4 text-primary" />
                <h2 className="font-semibold text-sm">Vulnerability Trend</h2>
                <span className="text-xs text-muted-foreground ml-auto">
                  {data.total_vulns_found} found · {data.total_fixed} fixed
                </span>
              </div>
              {data.vuln_trend.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
                  No scan data in this period
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={data.vuln_trend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id="foundGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="fixedGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#6b7280" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#6b7280" }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Area type="monotone" dataKey="found" name="Found" stroke="#ef4444" fill="url(#foundGrad)" strokeWidth={2} dot={false} />
                    <Area type="monotone" dataKey="fixed" name="Fixed" stroke="#10b981" fill="url(#fixedGrad)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* ── Bottom row: top vulns + severity dist ── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

              {/* Top vulnerability types */}
              <div className="rounded-xl border border-border/50 bg-card/60 p-6 backdrop-blur-sm">
                <h2 className="font-semibold text-sm mb-6 flex items-center gap-2">
                  <BarChart2 className="h-4 w-4 text-primary" />
                  Top Vulnerability Types
                </h2>
                {data.top_vulns.length === 0 ? (
                  <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
                    No vulnerabilities found in this period
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={data.top_vulns} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 10, fill: "#6b7280" }} tickLine={false} axisLine={false} allowDecimals={false} />
                      <YAxis type="category" dataKey="type" tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} axisLine={false} width={120} />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                        {data.top_vulns.map((_, i) => (
                          <Cell key={i} fill={CHART_COLOURS[i % CHART_COLOURS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>

              {/* Severity distribution */}
              <div className="rounded-xl border border-border/50 bg-card/60 p-6 backdrop-blur-sm">
                <h2 className="font-semibold text-sm mb-6 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  Severity Distribution
                </h2>
                {severityPieData.length === 0 ? (
                  <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
                    No severity data in this period
                  </div>
                ) : (
                  <div className="flex items-center gap-6">
                    <ResponsiveContainer width="60%" height={200}>
                      <PieChart>
                        <Pie
                          data={severityPieData}
                          cx="50%" cy="50%"
                          innerRadius={55} outerRadius={80}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {severityPieData.map((entry, i) => (
                            <Cell
                              key={i}
                              fill={SEVERITY_COLOURS[entry.name] ?? CHART_COLOURS[i % CHART_COLOURS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip content={<ChartTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                    {/* Legend */}
                    <div className="space-y-2">
                      {severityPieData.map((entry) => (
                        <div key={entry.name} className="flex items-center gap-2 text-xs">
                          <div
                            className="h-2.5 w-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: SEVERITY_COLOURS[entry.name] ?? "#6b7280" }}
                          />
                          <span className="text-muted-foreground">{entry.name}</span>
                          <span className="font-semibold ml-auto">{entry.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
