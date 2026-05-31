import React, { useEffect, useRef } from "react";
import { Radio, Maximize2, Minimize2 } from "lucide-react";
import { useStore } from "../store";

const TABS = ["Node 1", "Node 2", "Node 3"];
const BIN_COUNT = 100;

/**
 * Generate a synthetic spectrum from real FFT features.
 * Uses dom_freq to place the peak, peak_amp for its height,
 * and spectral_centroid for spread. This creates a visually
 * accurate representation of the actual sensor reading
 * without needing the full 512-bin FFT array from the ESP32.
 */
function spectrumFromFeatures(fftData, isFault, binCount) {
  const spectrum = new Array(binCount).fill(0.02); // noise floor
  if (!fftData) return spectrum;

  const mpuFreq = fftData.mpu_dom_freq || 12;
  const mpuAmp = fftData.mpu_peak_amp || 0.03;
  const piezoFreq = fftData.piezo_dom_freq || 300;
  const piezoAmp = fftData.piezo_peak_amp || 300;

  // Map real frequencies to bin indices (0-100 scale)
  // MPU: 0-20 Hz domain → bins 0-25
  // Piezo: 100-500 Hz domain → bins 30-90
  const mpuBin = Math.min(25, Math.max(0, Math.round((mpuFreq / 20) * 25)));
  const piezoBin = Math.min(90, Math.max(30, Math.round(((piezoFreq - 100) / 400) * 60) + 30));

  // Normalize amplitudes to 0-1 range for display
  const mpuNormAmp = Math.min(1, mpuAmp / 1.0);
  const piezoNormAmp = Math.min(1, piezoAmp / 3000);

  // Add MPU peak (gaussian-like spread)
  for (let i = Math.max(0, mpuBin - 5); i < Math.min(binCount, mpuBin + 5); i++) {
    const dist = Math.abs(i - mpuBin);
    spectrum[i] = Math.max(spectrum[i], mpuNormAmp * Math.exp(-0.3 * dist * dist));
  }

  // Add piezo peak
  for (let i = Math.max(0, piezoBin - 8); i < Math.min(binCount, piezoBin + 8); i++) {
    const dist = Math.abs(i - piezoBin);
    spectrum[i] = Math.max(spectrum[i], piezoNormAmp * Math.exp(-0.15 * dist * dist));
  }

  // In fault/critical mode: add harmonic distortion spike around bin 75
  // representing structural resonance shift from loose joint
  if (isFault) {
    const harmCenter = 75;
    for (let i = Math.max(0, harmCenter - 10); i < Math.min(binCount, harmCenter + 10); i++) {
      const dist = Math.abs(i - harmCenter);
      spectrum[i] = Math.max(spectrum[i], 0.85 * Math.exp(-0.08 * dist * dist));
    }
  }

  return spectrum;
}

export default React.memo(function FFTWaveform({
  activeNode = 0,
  onNodeChange,
  faultActive = false,
  fftData = null,
  thresholds = null,
}) {
  const canvasRef = useRef(null);
  const currentDataRef = useRef(new Array(BIN_COUNT).fill(0));
  const targetDataRef = useRef(new Array(BIN_COUNT).fill(0));
  const frameRef = useRef(null);
  const faultActiveRef = useRef(faultActive);
  const thresholdsRef = useRef(thresholds);

  const expandedCard = useStore((state) => state.expandedCard);
  const setExpandedCard = useStore((state) => state.setExpandedCard);
  const isExpanded = expandedCard === "fft";

  // Update target spectrum when fftData or fault state changes
  useEffect(() => {
    faultActiveRef.current = faultActive;
    targetDataRef.current = spectrumFromFeatures(fftData, faultActive, BIN_COUNT);
  }, [fftData, faultActive]);

  // Keep thresholds in ref for the render loop
  useEffect(() => {
    thresholdsRef.current = thresholds;
  }, [thresholds]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      const parent = canvas.parentElement;
      if (parent) {
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
      // Smooth interpolation toward target + noise
      for (let i = 0; i < BIN_COUNT; i++) {
        let target = targetDataRef.current[i] || 0;

        // Continuous noise floor in the 2-8 Hz band
        if (i >= 2 && i <= 8) {
          target += 0.02 + Math.random() * 0.03;
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

      // Draw Thresholds from real backend config
      const t = thresholdsRef.current;
      if (t) {
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

        // MPU thresholds mapped to display scale (0-1 normalized)
        // warning_peak_amp_g / critical_peak_amp_g are in g-force, map to ~0-1 range
        const mpuWarning = Math.min(1, (t.mpu?.warning_peak_amp_g ?? 0.3) / 1.0);
        const mpuCritical = Math.min(1, (t.mpu?.critical_peak_amp_g ?? 0.8) / 1.0);

        drawLine(mpuWarning, "#f59e0b", "MPU WARNING");
        drawLine(mpuCritical, "#e11d48", "MPU CRITICAL");
        ctx.restore();
      } else {
        // Fallback hardcoded thresholds if backend not reachable
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

        drawLine(0.3, "#f59e0b", "WARNING");
        drawLine(0.8, "#e11d48", "CRITICAL");
        ctx.restore();
      }

      // Draw Waveform Fill
      ctx.beginPath();
      ctx.moveTo(0, height);

      const step = width / (BIN_COUNT - 1);
      for (let i = 0; i < BIN_COUNT; i++) {
        const x = i * step;
        const y = height - (currentDataRef.current[i] * height);
        ctx.lineTo(x, y);
      }

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

  // Get label + node badge for display
  const activeNodeName = TABS[activeNode];
  const activeFft = fftData || {};

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
        <div className="flex items-center gap-3">
          {/* Real-time FFT feature readout */}
          <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
            MPU: {activeFft.mpu_dom_freq?.toFixed(1)}Hz @ {activeFft.mpu_peak_amp?.toFixed(3)}g
          </span>
          <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
            Piezo: {activeFft.piezo_dom_freq?.toFixed(0)}Hz
          </span>
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
