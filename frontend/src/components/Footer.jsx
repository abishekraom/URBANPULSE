import React, { useState, useEffect } from "react";
import { Wifi, WifiOff, Clock, Gauge, Zap } from "lucide-react";

export default React.memo(function Footer({ wsConnected = false }) {
  const [uptime, setUptime] = useState(0);
  const [latency, setLatency] = useState({ A: 12, B: 18, C: 9 });

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => {
      setUptime(Math.floor((Date.now() - start) / 1000));
      // Randomize latency slightly for realism
      if (Math.random() > 0.4) {
        setLatency((prev) => ({
          A: Math.max(5, prev.A + Math.floor(Math.random() * 5 - 2)),
          B: Math.max(5, prev.B + Math.floor(Math.random() * 5 - 2)),
          C: Math.max(5, prev.C + Math.floor(Math.random() * 5 - 2)),
        }));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatUptime = (seconds) => {
    const h = Math.floor(seconds / 3600).toString().padStart(2, "0");
    const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${h}:${m}:${s}`;
  };

  const nodes = [
    { name: "Node A", connected: wsConnected, latency: wsConnected ? `${latency.A}ms` : "---" },
    { name: "Node B", connected: wsConnected, latency: wsConnected ? `${latency.B}ms` : "---" },
    { name: "Node C", connected: wsConnected, latency: wsConnected ? `${latency.C}ms` : "---" },
  ];

  return (
    <div className="flex items-center gap-6">
      {/* Node connection indicators */}
      <div className="flex items-center gap-4">
        {nodes.map((n) => (
          <div key={n.name} className="flex items-center gap-1.5">
            {n.connected ? (
              <Wifi size={10} strokeWidth={1.5} style={{ color: "#22c55e" }} />
            ) : (
              <WifiOff size={10} strokeWidth={1.5} style={{ color: "#ef4444" }} />
            )}
            <span className="text-[10px] font-mono text-[var(--color-text-secondary)]">
              {n.name}
            </span>
            <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
              {n.connected ? n.latency : "disconnected"}
            </span>
          </div>
        ))}
      </div>

      {/* Tech stats */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Gauge size={10} strokeWidth={1.5} style={{ color: "#06b6d4" }} />
          <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
            1kHz sampling
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Zap size={10} strokeWidth={1.5} style={{ color: wsConnected ? "#f59e0b" : "#64748b" }} />
          <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
            {wsConnected ? "WebSocket: Connected" : "WebSocket: Disconnected"}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock size={10} strokeWidth={1.5} style={{ color: "#64748b" }} />
          <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
            Uptime {formatUptime(uptime)}
          </span>
        </div>
      </div>
    </div>
  );
});
