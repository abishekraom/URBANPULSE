import React from "react";
import { Map, Maximize2, Minimize2 } from "lucide-react";
import { useStore } from "../store";

const NODES = [
  { id: "A", idx: 0, x: 25, y: 30 },
  { id: "B", idx: 1, x: 55, y: 65 },
  { id: "C", idx: 2, x: 80, y: 35 },
];

const STATUS_HEX = {
  healthy: "#10b981",
  warning: "#f59e0b",
  critical: "#e11d48",
};

function getStatus(score) {
  if (score >= 80) return "healthy";
  if (score >= 40) return "warning";
  return "critical";
}

export default React.memo(function StructuralMap({ activeNode = 0, nodeScores = {} }) {
  const expandedCard = useStore((state) => state.expandedCard);
  const setExpandedCard = useStore((state) => state.setExpandedCard);
  const isExpanded = expandedCard === "map";

  return (
    <div
      id="structural-map-panel"
      className={`card-glass p-5 flex flex-col gap-2 transition-all duration-300 ${
        isExpanded ? "fixed inset-[10%] z-50 bg-slate-950 shadow-2xl" : "h-full animate-slide-in relative"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Map size={14} strokeWidth={1.5} style={{ color: "#06b6d4" }} />
          <h2 className="text-xs font-semibold tracking-wider uppercase text-[var(--color-text-primary)]">
            SVG Structural Map
          </h2>
        </div>
        <button 
          onClick={() => setExpandedCard(isExpanded ? null : "map")}
          className="p-1 rounded-sm hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
        >
          {isExpanded ? (
            <Minimize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          ) : (
            <Maximize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          )}
        </button>
      </div>

      {/* Map area */}
      <div
        className="flex-1 relative rounded-sm overflow-hidden"
        style={{ background: "#020617" }}
      >
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Grid pattern */}
          <defs>
            <pattern
              id="grid"
              width="10"
              height="10"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 10 0 L 0 0 0 10"
                fill="none"
                stroke="#1e293b"
                strokeWidth="0.3"
              />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="url(#grid)" />

          {/* Structure outline */}
          <rect
            x="12"
            y="15"
            width="76"
            height="70"
            rx="2"
            fill="none"
            stroke="#334155"
            strokeWidth="0.6"
            strokeDasharray="2 1"
          />
          {/* Internal structural members */}
          <line x1="12" y1="50" x2="88" y2="50" stroke="#334155" strokeWidth="0.4" strokeDasharray="1.5 1" />
          <line x1="50" y1="15" x2="50" y2="85" stroke="#334155" strokeWidth="0.4" strokeDasharray="1.5 1" />
          {/* Diagonal bracing */}
          <line x1="12" y1="15" x2="50" y2="50" stroke="rgba(71,85,105,0.2)" strokeWidth="0.3" />
          <line x1="88" y1="15" x2="50" y2="50" stroke="rgba(71,85,105,0.2)" strokeWidth="0.3" />

          {/* Connection lines between nodes */}
          {NODES.map((node, i) => {
            const next = NODES[(i + 1) % NODES.length];
            return (
              <line
                key={`line-${node.id}-${next.id}`}
                x1={node.x}
                y1={node.y}
                x2={next.x}
                y2={next.y}
                stroke="#06b6d4"
                strokeWidth="0.3"
                strokeDasharray="2 2"
                opacity="0.4"
              />
            );
          })}

          {/* Node markers */}
          {NODES.map((node) => {
            const isActive = node.idx === activeNode;
            const nodeKey = `Node ${node.id}`;
            const score = nodeScores[nodeKey] ?? 90;
            const status = getStatus(score);
            const color = STATUS_HEX[status];

            return (
              <g key={node.id}>
                {/* Pulse ring only on critical */}
                {status === "critical" && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="5"
                    fill="none"
                    stroke={color}
                    strokeWidth="0.5"
                    className="animate-pulse-glow"
                  />
                )}

                {/* Sharp Dot */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="2"
                  fill={color}
                  stroke={isActive ? "#f8fafc" : "none"}
                  strokeWidth="0.4"
                  style={{ transition: "all 0.3s ease" }}
                />

                {/* Label */}
                <text
                  x={node.x}
                  y={node.y - (isActive ? 7 : 5)}
                  textAnchor="middle"
                  fill={isActive ? "#f8fafc" : "#94a3b8"}
                  fontSize={isActive ? "4" : "3.5"}
                  fontFamily="'Geist Mono', monospace"
                  fontWeight={isActive ? "700" : "600"}
                  style={{ transition: "fill 0.3s ease, font-size 0.3s ease" }}
                >
                  Node {node.id}
                </text>

                {/* Active indicator text */}
                {isActive && (
                  <text
                    x={node.x}
                    y={node.y + 6}
                    textAnchor="middle"
                    fill="#0ea5e9"
                    fontSize="2.5"
                    fontFamily="'Geist Mono', monospace"
                    fontWeight="600"
                    opacity="0.9"
                  >
                    ● FFT ACTIVE
                  </text>
                )}
              </g>
            );
          })}

          {/* Scale label */}
          <text
            x="50"
            y="96"
            textAnchor="middle"
            fill="#64748b"
            fontSize="2.5"
            fontFamily="'Geist Mono', monospace"
          >
            STRUCTURAL FRAME — TOP VIEW
          </text>
        </svg>
      </div>
    </div>
  );
});
