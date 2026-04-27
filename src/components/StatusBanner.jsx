import React from "react";
import { ShieldCheck, ShieldAlert, Activity, Maximize } from "lucide-react";

const STATUS_STYLES = {
  clear: {
    hex: "#10b981",
    label: "SYSTEM STATUS: ALL CLEAR",
    bg: "rgba(16,185,129,0.05)",
    border: "rgba(16,185,129,0.2)",
    glow: "",
    Icon: ShieldCheck,
  },
  warning: {
    hex: "#f59e0b",
    label: "SYSTEM STATUS: WARNING",
    bg: "rgba(245,158,11,0.05)",
    border: "rgba(245,158,11,0.2)",
    glow: "",
    Icon: ShieldAlert,
  },
  critical: {
    hex: "#e11d48",
    label: "SYSTEM STATUS: CRITICAL",
    bg: "rgba(225,29,72,0.05)",
    border: "rgba(225,29,72,0.2)",
    glow: "",
    Icon: ShieldAlert,
  },
};

export default React.memo(function StatusBanner({ systemStatus = "clear" }) {
  const s = STATUS_STYLES[systemStatus] || STATUS_STYLES.clear;
  const Icon = s.Icon;

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch((err) => {
        console.log(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };

  return (
    <div
      id="status-banner"
      className={`w-full px-4 py-2.5 flex items-center justify-between transition-all duration-500`}
      style={{ background: s.bg, borderBottom: `1px solid ${s.border}` }}
    >
      {/* Left — branding */}
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: "rgba(6,182,212,0.15)" }}
        >
          <Activity size={18} strokeWidth={1.5} style={{ color: "#06b6d4" }} />
        </div>
        <div className="leading-tight">
          <span className="text-xs font-semibold tracking-widest uppercase text-[var(--color-text-secondary)]">
            UrbanPulse
          </span>
          <span className="text-xs text-[var(--color-text-muted)] ml-2 hidden sm:inline">
            Structural Health Monitor
          </span>
        </div>
      </div>

      {/* Center — status */}
      <div className="flex items-center gap-3">
        <span className="relative flex h-3 w-3">
          <span
            className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
            style={{ background: s.hex }}
          />
          <span
            className="relative inline-flex rounded-full h-3 w-3"
            style={{ background: s.hex }}
          />
        </span>
        <span
          className="font-mono text-xl font-bold tracking-widest transition-colors duration-400"
          style={{ color: s.hex }}
        >
          {s.label}
        </span>
        <Icon size={20} strokeWidth={1.5} style={{ color: s.hex }} />
      </div>

      {/* Right — timestamp & fullscreen */}
      <div className="flex items-center gap-4">
        <div className="text-sm font-mono text-[var(--color-text-muted)] hidden md:block">
          <Clock />
        </div>
        <button
          onClick={toggleFullscreen}
          className="p-1.5 rounded-md hover:bg-[rgba(255,255,255,0.1)] transition-colors cursor-pointer text-[var(--color-text-muted)] hover:text-white"
          aria-label="Toggle Fullscreen"
        >
          <Maximize size={16} strokeWidth={1.5} />
        </button>
      </div>
    </div>
  );
});

const Clock = () => {
  const [time, setTime] = React.useState(new Date().toLocaleTimeString("en-US", { hour12: false }));
  React.useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString("en-US", { hour12: false }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);
  return <>{time}</>;
};
