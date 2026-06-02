import React from "react";
import { Cpu, Wifi, WifiOff } from "lucide-react";

const STATUS_CONFIG = {
  healthy: {
    hex: "#10b981",
    label: "HEALTHY",
  },
  warning: {
    hex: "#f59e0b",
    label: "WARNING",
  },
  critical: {
    hex: "#e11d48",
    label: "CRITICAL",
  },
  offline: {
    hex: "#64748b",
    label: "OFFLINE",
  },
  waiting: {
    hex: "#334155",
    label: "WAITING",
  },
};

export default React.memo(function NodeCard({
  name,
  score = 92,
  state = "ONLINE",
  severity = "NORMAL",
  readings = { accelX: "—", accelY: "—", piezo: "—" },
}) {
  const isOnline = state !== "OFFLINE" && state !== "WAITING";
  // Use backend severity when available, fall back to score-based status
  const status = !isOnline ? state.toLowerCase() : (severity === "CRITICAL" ? "critical" : severity === "WARNING" ? "warning" : score >= 80 ? "healthy" : score >= 40 ? "warning" : "critical");
  const color = STATUS_CONFIG[status]?.hex || "#334155";

  // Gauge always shows 0 when offline
  const displayScore = isOnline ? score : 0;
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (displayScore / 100) * circumference;

  return (
    <div
      id={`node-card-${name.toLowerCase().replace(/\s/g, "-")}`}
      className="card-glass p-5 flex flex-col items-center gap-3 animate-slide-in cursor-pointer"
      style={{ opacity: isOnline ? 1 : 0.6 }}
    >
      <div className="w-full flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu size={14} strokeWidth={1.5} style={{ color: isOnline ? "#06b6d4" : "#64748b" }} />
          <span className="text-xs font-semibold tracking-wider uppercase text-[var(--color-text-secondary)]">
            {name}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {isOnline ? (
            <Wifi size={12} strokeWidth={1.5} style={{ color }} />
          ) : (
            <WifiOff size={12} strokeWidth={1.5} style={{ color: "#64748b" }} />
          )}
          <span
            className="text-[10px] font-mono font-medium"
            style={{ color }}
          >
            {STATUS_CONFIG[status].label}
          </span>
        </div>
      </div>

      <div className="relative w-24 h-24 flex items-center justify-center">
        <svg width="96" height="96" viewBox="0 0 96 96" className="absolute inset-0 transform -rotate-90">
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="transparent"
            stroke="#1e293b"
            strokeWidth="3"
          />
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="transparent"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-300 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span
            className="text-2xl font-bold font-mono transition-colors duration-300"
            style={{ color }}
          >
            {isOnline ? score : "—"}
          </span>
          <span className="text-[9px] uppercase tracking-widest text-[var(--color-text-muted)]">
            {isOnline ? "Health" : "Offline"}
          </span>
        </div>
      </div>

      <div className="w-full grid grid-cols-3 gap-1">
        {[
          { label: "Accel X", value: isOnline ? readings.accelX : "—", id: `${name}-accelX` },
          { label: "Accel Y", value: isOnline ? readings.accelY : "—", id: `${name}-accelY` },
          { label: "Piezo", value: isOnline ? readings.piezo : "—", id: `${name}-piezo` },
        ].map((stat) => (
          <div
            key={stat.label}
            className="text-center py-1 rounded-sm"
            style={{ background: "rgba(15,23,42,0.5)" }}
          >
            <div className="text-[9px] text-[var(--color-text-muted)] uppercase tracking-wider">
              {stat.label}
            </div>
            <div id={stat.id} className="text-xs font-mono font-medium text-[var(--color-text-secondary)]">
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
