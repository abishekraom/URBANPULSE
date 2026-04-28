import React, { useEffect, useRef } from "react";
import { Bell, AlertTriangle, CheckCircle, XCircle, Download, Maximize2, Minimize2 } from "lucide-react";
import { useStore } from "../store";

const CFG = {
  critical: { icon: XCircle, color: "#e11d48", bg: "rgba(225,29,72,0.1)", border: "rgba(225,29,72,0.3)" },
  warning: { icon: AlertTriangle, color: "#f59e0b", bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.25)" },
  healthy: { icon: CheckCircle, color: "#10b981", bg: "rgba(16,185,129,0.08)", border: "rgba(16,185,129,0.2)" },
};

export default React.memo(function AlertTimeline({ events = [] }) {
  const scrollRef = useRef(null);

  const expandedCard = useStore((state) => state.expandedCard);
  const setExpandedCard = useStore((state) => state.setExpandedCard);
  const isExpanded = expandedCard === "alerts";

  /* Auto-scroll to top when new events are prepended */
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events.length]);

  const exportCSV = () => {
    const headers = "Timestamp,Node,Severity,Message\n";
    const rows = events
      .map((e) => `"${e.time}","${e.node}","${e.level}","${e.msg}"`)
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "urbanpulse_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div id="alert-timeline-panel" className={`card-glass p-5 flex flex-col gap-2 transition-all duration-300 ${
      isExpanded ? "fixed inset-[10%] z-50 bg-slate-950 shadow-2xl" : "h-full animate-slide-in relative"
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell size={14} strokeWidth={1.5} style={{ color: "#f59e0b" }} />
          <h2 className="text-xs font-semibold tracking-wider uppercase text-[var(--color-text-primary)]">
            Alert Timeline
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-[var(--color-text-muted)] uppercase">
            {events.length} events
          </span>
          <button
            onClick={exportCSV}
            className="flex items-center gap-1.5 px-2 py-1 rounded-sm border transition-colors cursor-pointer"
            style={{
              background: "rgba(15,23,42,0.5)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-secondary)",
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = "#f8fafc")}
            onMouseOut={(e) =>
              (e.currentTarget.style.color = "var(--color-text-secondary)")
            }
          >
            <Download size={10} strokeWidth={1.5} />
            <span className="text-[9px] font-mono uppercase tracking-wider">
              Export CSV
            </span>
          </button>
          <button
            onClick={() => setExpandedCard(isExpanded ? null : "alerts")}
            className="p-1 rounded-sm border transition-colors cursor-pointer ml-1"
            style={{
              background: "rgba(15,23,42,0.5)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-secondary)",
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = "#f8fafc")}
            onMouseOut={(e) =>
              (e.currentTarget.style.color = "var(--color-text-secondary)")
            }
          >
            {isExpanded ? (
              <Minimize2 size={12} strokeWidth={1.5} />
            ) : (
              <Maximize2 size={12} strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>

      {/* Event list */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-1.5 pr-1"
        style={{ minHeight: 0 }}
      >
        {events.map((e, i) => {
          const c = CFG[e.level] || CFG.healthy;
          const Icon = c.icon;
          return (
            <div
              key={e.id || i}
              className="flex gap-2.5 p-2 rounded-sm transition-all duration-200 hover:bg-[var(--color-bg-card-hover)] cursor-pointer"
              style={{
                background: c.bg,
                borderLeft: `3px solid ${c.border}`,
                animation: i === 0 ? "slide-in-up 0.3s ease-out" : "none",
              }}
            >
              <Icon
                size={14}
                strokeWidth={1.5}
                style={{ color: c.color }}
                className="flex-shrink-0 mt-0.5"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span
                    className="text-[10px] font-mono font-semibold"
                    style={{ color: c.color }}
                  >
                    {e.node}
                  </span>
                  <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
                    {e.time}
                  </span>
                  <span
                    className="text-[8px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded-sm"
                    style={{
                      color: c.color,
                      background: c.bg,
                      border: `1px solid ${c.border}`,
                    }}
                  >
                    {e.level}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-[var(--color-text-secondary)] leading-relaxed truncate">
                  {e.msg}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});
