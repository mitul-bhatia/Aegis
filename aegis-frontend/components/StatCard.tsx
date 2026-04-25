"use client";

interface StatCardProps {
  icon: string;
  value: number | string;
  label: string;
  color?: string;
  pulse?: boolean;
}

export function StatCard({ icon, value, label, color = "#7c3aed", pulse = false }: StatCardProps) {
  return (
    <div
      className="bg-slate-900 border border-slate-700 rounded-xl p-4 flex items-center gap-4
                 hover:border-slate-500 transition-all"
      style={{ boxShadow: pulse ? `0 0 16px ${color}33` : undefined }}
    >
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0"
        style={{ backgroundColor: `${color}22`, border: `1px solid ${color}44` }}
      >
        {icon}
      </div>
      <div>
        <div className="text-2xl font-bold font-mono text-slate-100">{value}</div>
        <div className="text-xs text-slate-400">{label}</div>
      </div>
    </div>
  );
}
