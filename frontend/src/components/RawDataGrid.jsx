import React from "react";
import { Database, Maximize2, Minimize2 } from "lucide-react";
import { useStore } from "../store";

export default React.memo(function RawDataGrid({ nodes = {} }) {
  const expandedCard = useStore((state) => state.expandedCard);
  const setExpandedCard = useStore((state) => state.setExpandedCard);
  const isExpanded = expandedCard === "rawdata";

  return (
    <div className={`card-glass p-5 flex flex-col gap-2 transition-all duration-300 ${
      isExpanded ? "fixed inset-[10%] z-50 bg-slate-950 shadow-2xl" : "h-full animate-slide-in relative"
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database size={14} strokeWidth={1.5} style={{ color: "#8b5cf6" }} />
          <h2 className="text-xs font-semibold tracking-wider uppercase text-[var(--color-text-primary)]">
            Raw Telemetry
          </h2>
        </div>
        <button 
          onClick={() => setExpandedCard(isExpanded ? null : "rawdata")}
          className="p-1 rounded-sm hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
        >
          {isExpanded ? (
            <Minimize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          ) : (
            <Maximize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          )}
        </button>
      </div>
      
      <div
        className="flex-1 overflow-auto rounded border"
        style={{
          borderColor: "rgba(51,65,85,0.5)",
          background: "rgba(15,23,42,0.6)",
        }}
      >
        <table className="w-full table-fixed text-[10px] font-mono tabular-nums text-left whitespace-nowrap">
          <thead
            className="sticky top-0 border-b text-[var(--color-text-muted)]"
            style={{
              background: "rgba(15,23,42,0.95)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <tr>
              <th className="w-1/4 px-3 py-2 font-semibold">NODE</th>
              <th className="w-1/4 px-3 py-2 font-semibold">ACCEL X</th>
              <th className="w-1/4 px-3 py-2 font-semibold">ACCEL Y</th>
              <th className="w-1/4 px-3 py-2 font-semibold">PIEZO ADC</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[rgba(51,65,85,0.3)]">
            {Object.entries(nodes).map(([name, data]) => (
              <tr key={name} className="hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                <td className="px-3 py-2 text-[var(--color-text-secondary)] font-semibold">
                  {name}
                </td>
                <td className="px-3 py-2 text-[var(--color-text-primary)]">
                  {data.readings.accelX}
                </td>
                <td className="px-3 py-2 text-[var(--color-text-primary)]">
                  {data.readings.accelY}
                </td>
                <td className="px-3 py-2 text-[var(--color-text-primary)]">
                  {data.readings.piezo}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});
