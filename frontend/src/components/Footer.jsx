import React, { useState, useEffect } from "react";
import { Wifi, WifiOff, Clock, Gauge, Zap, Activity } from "lucide-react";

export default React.memo(function Footer({ wsConnected = false, nodes = {} }) {
  const [health, setHealth] = useState({
    uptime_s: 0,
    total_packets: 0,
    last_packet_age_ms: 0,
  });

  // Poll /api/health every 5s for real backend metrics
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch {
        // Backend not reachable — use previous values
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatUptime = (seconds) => {
    const h = Math.floor(seconds / 3600).toString().padStart(2, "0");
    const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${h}:${m}:${s}`;
  };

  const formatPacketAge = (ms) => {
    if (ms === 0) return "—";
    if (ms < 1000) return `${ms}ms ago`;
    if (ms < 60000) return `${Math.floor(ms / 1000)}s ago`;
    return `${Math.floor(ms / 60000)}m ago`;
  };

  // Build per-node status from WebSocket node updates
  const nodeEntries = Object.entries(nodes);
  const nodeStatuses = nodeEntries.map(([name, data]) => ({
    name,
    connected: wsConnected && data.state !== "OFFLINE",
    score: data.score ?? 100,
  }));

  return (
    <div className="flex items-center gap-6">
      {/* Node connection indicators */}
      <div className="flex items-center gap-4">
        {nodeStatuses.length > 0 ? (
          nodeStatuses.map((n) => (
            <div key={n.name} className="flex items-center gap-1.5">
              {n.connected ? (
                <Wifi size={10} strokeWidth={1.5} style={{ color: "#22c55e" }} />
              ) : (
                <WifiOff size={10} strokeWidth={1.5} style={{ color: "#ef4444" }} />
              )}
              <span className="text-[10px] font-mono text-[var(--color-text-secondary)]">
                {n.name}
              </span>
              <span
                className="text-[9px] font-mono"
                style={{ color: n.connected ? "#22c55e" : "#ef4444" }}
              >
                {n.connected ? `${n.score}%` : "offline"}
              </span>
            </div>
          ))
        ) : (
          <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
            No node data
          </span>
        )}
      </div>

      {/* Real backend metrics */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Activity size={10} strokeWidth={1.5} style={{ color: "#06b6d4" }} />
          <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
            {health.total_packets} packets
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Gauge size={10} strokeWidth={1.5} style={{ color: "#8b5cf6" }} />
          <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
            Last: {formatPacketAge(health.last_packet_age_ms)}
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
            Uptime {formatUptime(health.uptime_s)}
          </span>
        </div>
      </div>
    </div>
  );
});
