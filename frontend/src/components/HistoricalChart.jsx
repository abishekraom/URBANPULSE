import React from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Activity, Maximize2, Minimize2 } from "lucide-react";
import { useStore } from "../store";

export default React.memo(function HistoricalChart({ data = [] }) {
  const expandedCard = useStore((state) => state.expandedCard);
  const setExpandedCard = useStore((state) => state.setExpandedCard);
  const isExpanded = expandedCard === "history";

  return (
    <div id="historical-chart-panel" className={`card-glass p-5 flex flex-col gap-2 transition-all duration-300 ${
      isExpanded ? "fixed inset-[10%] z-50 bg-slate-950 shadow-2xl" : "h-full animate-slide-in relative"
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={14} strokeWidth={1.5} style={{ color: "#10b981" }} />
          <h2 className="text-xs font-semibold tracking-wider uppercase text-[var(--color-text-primary)]">
            Health Score History
          </h2>
        </div>
        <button 
          onClick={() => setExpandedCard(isExpanded ? null : "history")}
          className="p-1 rounded-sm hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
        >
          {isExpanded ? (
            <Minimize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          ) : (
            <Maximize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          )}
        </button>
      </div>

      <div className="flex-1 min-h-0 relative">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" vertical={false} />
            <XAxis
              dataKey="time"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 9 }}
              minTickGap={30}
            />
            <YAxis
              domain={[0, 100]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 9 }}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(15,23,42,0.9)",
                border: "1px solid rgba(51,65,85,0.5)",
                fontSize: "10px",
                borderRadius: "4px",
              }}
            />
            <Line type="monotone" dataKey="Node A" stroke="#0ea5e9" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="Node B" stroke="#f59e0b" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="Node C" stroke="#8b5cf6" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
