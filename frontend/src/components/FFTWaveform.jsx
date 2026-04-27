import React, { useEffect, useRef } from "react";
import { Radio, Maximize2, Minimize2 } from "lucide-react";
import { useStore } from "../store";

const TABS = ["Node A", "Node B", "Node C"];
const BIN_COUNT = 100; 
const THRESHOLD_WARNING = 0.5;
const THRESHOLD_CRITICAL = 0.75;

// Helpers to generate baseline/faults
function baselineSpectrum(nodeIdx) {
  const base = new Array(BIN_COUNT).fill(0.02);
  const peaks = [
    [15, 0.15], // Node A
    [25, 0.12], // Node B
    [35, 0.18], // Node C
  ];
  const [center, amp] = peaks[nodeIdx] || [20, 0.1];
  return base.map((v, i) => {
    const dist = Math.abs(i - center);
    return v + Math.max(0, amp * Math.exp(-0.05 * dist * dist));
  });
}

function faultSpectrum(nodeIdx) {
  const base = baselineSpectrum(nodeIdx);
  // Spike at 60-90 Hz range (around 75)
  const spikeCenter = 75; 
  return base.map((v, i) => {
    const dist = Math.abs(i - spikeCenter);
    const spike = 0.95 * Math.exp(-0.15 * dist * dist);
    return Math.min(1, Math.max(v, spike));
  });
}

export default React.memo(function FFTWaveform({
  activeNode = 0,
  onNodeChange,
  faultActive = false,
}) {
  const canvasRef = useRef(null);

  const currentDataRef = useRef(new Array(BIN_COUNT).fill(0));
  const targetDataRef = useRef(baselineSpectrum(activeNode));
  const frameRef = useRef(null);
  const faultActiveRef = useRef(faultActive);
  
  const expandedCard = useStore((state) => state.expandedCard);
  const setExpandedCard = useStore((state) => state.setExpandedCard);
  const isExpanded = expandedCard === "fft";

  // Update target signal when node or fault state changes
  useEffect(() => {
    faultActiveRef.current = faultActive;
    if (faultActive) {
      targetDataRef.current = faultSpectrum(activeNode);
    } else {
      targetDataRef.current = baselineSpectrum(activeNode);
    }
  }, [activeNode, faultActive]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      const parent = canvas.parentElement;
      if (parent) {
        // Set actual internal canvas resolution to match display size for crispness
        const rect = parent.getBoundingClientRect();
        canvas.width = rect.width * window.devicePixelRatio;
        canvas.height = rect.height * window.devicePixelRatio;
      }
    };
    resize();

    const resizeObserver = new ResizeObserver(resize);
    if (canvas.parentElement) {
      resizeObserver.observe(canvas.parentElement);
    }

    const loop = () => {
      for (let i = 0; i < BIN_COUNT; i++) {
        let target = targetDataRef.current[i] || 0;
        
        // Continuous noise floor in the 2-8 Hz band
        if (i >= 2 && i <= 8) {
          target += 0.02 + Math.random() * 0.03; // Random value between 2% and 5%
        }

        const noise = (Math.random() - 0.5) * 0.05;
        const noisyTarget = Math.max(0, Math.min(1, target + noise));

        let current = currentDataRef.current[i] || 0;
        currentDataRef.current[i] = current + (noisyTarget - current) * 0.2;
      }

      // Draw
      const width = canvas.width;
      const height = canvas.height;
      
      ctx.clearRect(0, 0, width, height);

      const isCritical = faultActiveRef.current;
      const strokeColor = isCritical ? "#e11d48" : "#0ea5e9";
      const fillColor = isCritical ? "rgba(225, 29, 72, 0.15)" : "rgba(14, 165, 233, 0.15)";

      // Draw Thresholds
      ctx.save();
      ctx.lineWidth = 1 * window.devicePixelRatio;
      ctx.setLineDash([4 * window.devicePixelRatio, 4 * window.devicePixelRatio]);
      
      const drawLine = (val, color, label) => {
        const y = height - (val * height);
        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
        
        ctx.fillStyle = color;
        ctx.font = `${10 * window.devicePixelRatio}px 'Geist Mono', monospace`;
        ctx.fillText(label, 5 * window.devicePixelRatio, y - 5 * window.devicePixelRatio);
      };

      drawLine(THRESHOLD_WARNING, "#f59e0b", "WARNING THRESHOLD");
      drawLine(THRESHOLD_CRITICAL, "#e11d48", "CRITICAL THRESHOLD");
      ctx.restore();

      // Draw Waveform Fill
      ctx.beginPath();
      ctx.moveTo(0, height);
      
      const step = width / (BIN_COUNT - 1);
      for (let i = 0; i < BIN_COUNT; i++) {
        const x = i * step;
        const y = height - (currentDataRef.current[i] * height);
        ctx.lineTo(x, y);
      }
      
      // Complete path for fill
      ctx.lineTo(width, height);
      ctx.lineTo(0, height);
      ctx.closePath();
      
      ctx.fillStyle = fillColor;
      ctx.fill();

      // Draw Waveform Stroke
      ctx.beginPath();
      for (let i = 0; i < BIN_COUNT; i++) {
        const x = i * step;
        const y = height - (currentDataRef.current[i] * height);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.lineWidth = 1.5 * window.devicePixelRatio;
      ctx.strokeStyle = strokeColor;
      ctx.stroke();

      frameRef.current = requestAnimationFrame(loop);
    };

    frameRef.current = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(frameRef.current);
      resizeObserver.disconnect();
    };
  }, []); // Empty deps, read refs

  return (
    <div
      id="fft-waveform-panel"
      className={`card-glass p-5 flex flex-col gap-2 transition-all duration-300 ${
        isExpanded ? "fixed inset-[10%] z-50 bg-slate-950 shadow-2xl" : "h-full animate-slide-in relative"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio size={14} strokeWidth={1.5} style={{ color: "#0ea5e9" }} />
          <h2 className="text-xs font-semibold tracking-wider uppercase text-[var(--color-text-primary)]">
            Live FFT Waveform
          </h2>
          <span className="relative flex h-2 w-2 ml-1">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ background: faultActive ? "#e11d48" : "#10b981" }} />
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: faultActive ? "#e11d48" : "#10b981" }} />
          </span>
          <span className="text-[9px] font-mono uppercase" style={{ color: faultActive ? "#e11d48" : "#10b981" }}>Live</span>
        </div>
        <button 
          onClick={() => setExpandedCard(isExpanded ? null : "fft")}
          className="p-1 rounded-sm hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
        >
          {isExpanded ? (
            <Minimize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          ) : (
            <Maximize2 size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
          )}
        </button>
      </div>

      <div className="flex gap-1 p-0.5 rounded-sm" style={{ background: "rgba(15,23,42,0.6)" }}>
        {TABS.map((tab, i) => {
          const isActive = activeNode === i;
          return (
            <button
              key={tab}
              onClick={() => onNodeChange?.(i)}
              className={`flex-1 py-1 text-[11px] font-medium rounded-sm transition-all duration-200 cursor-pointer ${
                isActive ? "text-[var(--color-text-primary)] font-semibold" : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
              style={isActive ? { background: `rgba(30, 41, 59, 0.8)`, border: `1px solid #334155` } : { border: "1px solid transparent" }}
            >
              {tab}
            </button>
          );
        })}
      </div>

      <div className="flex-1 rounded border border-slate-800 overflow-hidden relative" style={{ background: "#020617" }}>
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" style={{ touchAction: "none" }} />
      </div>
    </div>
  );
});
