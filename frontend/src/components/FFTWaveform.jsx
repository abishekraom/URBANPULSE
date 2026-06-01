import React, { useEffect, useRef } from "react";
import { Radio, Maximize2, Minimize2 } from "lucide-react";
import { useStore } from "../store";

const TABS = ["Node 1", "Node 2", "Node 3"];
const BIN_COUNT = 100;

function makeSpectrum(data, fault, count) {
  var out = new Array(count);
  for (var i = 0; i < count; i++) out[i] = 0.02;
  if (!data) return out;
  var mf = data.mpu_dom_freq;
  var ma = data.mpu_peak_amp;
  var pf = data.piezo_dom_freq;
  var pa = data.piezo_peak_amp;
  // No fallback values — if data is 0/null, no peaks generated
  if (!mf && !ma && !pf && !pa) return out;
  var mbin = Math.min(25, Math.max(0, Math.round((mf / 20) * 25)));
  var pbin = Math.min(90, Math.max(30, Math.round(((pf - 100) / 400) * 60) + 30));
  var mn = Math.min(1, ma / 1.0);
  var pn = Math.min(1, pa / 3000);
  for (var i = Math.max(0, mbin - 5); i < Math.min(count, mbin + 5); i++) {
    out[i] = Math.max(out[i], mn * Math.exp(-0.3 * (i - mbin) * (i - mbin)));
  }
  for (var i = Math.max(0, pbin - 8); i < Math.min(count, pbin + 8); i++) {
    out[i] = Math.max(out[i], pn * Math.exp(-0.15 * (i - pbin) * (i - pbin)));
  }
  if (fault) {
    for (var i = 65; i < 85; i++) {
      out[i] = Math.max(out[i] || 0, 0.85 * Math.exp(-0.08 * (i - 75) * (i - 75)));
    }
  }
  return out;
}

function FFTWaveform(props) {
  var activeNode = props.activeNode || 0;
  var onNodeChange = props.onNodeChange;
  var faultActive = props.faultActive || false;
  var fftData = props.fftData || null;
  var thresholds = props.thresholds || null;

  var canvasRef = useRef(null);
  var dataRef = useRef(new Float64Array(BIN_COUNT));
  var targetRef = useRef(new Float64Array(BIN_COUNT));
  var faultRef = useRef(faultActive);
  var threshRef = useRef(thresholds);
  var rafRef = useRef(null);
  var idleRef = useRef(true);
  var tickRef = useRef(0);
  var kickRef = useRef(null);
  var lastDataMs = useRef(0);

  faultRef.current = faultActive;
  threshRef.current = thresholds;

  // When fftData changes: update target, reset tick, kick animation
  var prevRef = useRef(null);
  if (fftData !== prevRef.current) {
    prevRef.current = fftData;
    lastDataMs.current = Date.now();
    var s = makeSpectrum(fftData, faultActive, BIN_COUNT);
    for (var i = 0; i < BIN_COUNT; i++) targetRef.current[i] = s[i];
    tickRef.current = 0;
    if (idleRef.current && canvasRef.current) {
      idleRef.current = false;
      if (kickRef.current) kickRef.current();
    }
  }

  var expandedCard = useStore(function(s) { return s.expandedCard; });
  var setExpandedCard = useStore(function(s) { return s.setExpandedCard; });
  var isExpanded = expandedCard === "fft";

  useEffect(function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var dpr = window.devicePixelRatio || 1;

    function size() {
      var p = canvas.parentElement;
      if (!p) return;
      var r = p.getBoundingClientRect();
      canvas.width = r.width * dpr;
      canvas.height = r.height * dpr;
      canvas.style.width = r.width + "px";
      canvas.style.height = r.height + "px";
    }
    size();
    var ro = new ResizeObserver(size);
    if (canvas.parentElement) ro.observe(canvas.parentElement);

    function drawFrame() {
      var w = canvas.width, h = canvas.height;
      if (w < 2 || h < 2) return;
      ctx.clearRect(0, 0, w, h);

      var t = threshRef.current;
      ctx.save();
      ctx.lineWidth = 1 * dpr;
      ctx.setLineDash([4 * dpr, 4 * dpr]);
      function dl(val, color, label) {
        var y = h - (val * h);
        ctx.strokeStyle = color;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        ctx.fillStyle = color;
        ctx.font = (10 * dpr) + "px monospace";
        ctx.fillText(label, 5 * dpr, y - 5 * dpr);
      }
      if (t) {
        dl(Math.min(1, (t.mpu ? t.mpu.warning_peak_amp_g : 0.3) / 1.0), "#f59e0b", "MPU WARNING");
        dl(Math.min(1, (t.mpu ? t.mpu.critical_peak_amp_g : 0.8) / 1.0), "#e11d48", "MPU CRITICAL");
      } else {
        dl(0.3, "#f59e0b", "WARNING");
        dl(0.8, "#e11d48", "CRITICAL");
      }
      ctx.restore();

      var crit = faultRef.current;
      var strokeC = crit ? "#e11d48" : "#0ea5e9";
      var fillC = crit ? "rgba(225,29,72,0.15)" : "rgba(14,165,233,0.15)";
      var step = w / (BIN_COUNT - 1);

      ctx.beginPath();
      ctx.moveTo(0, h);
      for (var i = 0; i < BIN_COUNT; i++) ctx.lineTo(i * step, h - (dataRef.current[i] * h));
      ctx.lineTo(w, h); ctx.closePath();
      ctx.fillStyle = fillC; ctx.fill();

      ctx.beginPath();
      for (var i = 0; i < BIN_COUNT; i++) {
        var y = h - (dataRef.current[i] * h);
        if (i === 0) ctx.moveTo(0, y); else ctx.lineTo(i * step, y);
      }
      ctx.lineWidth = 1.5 * dpr;
      ctx.strokeStyle = strokeC; ctx.stroke();
    }

    function hasSignal(arr) {
      for (var i = 0; i < BIN_COUNT; i++) {
        if (arr[i] > 0.05) return true;
      }
      return false;
    }

    function animate() {
      rafRef.current = null;
      if (!ctx) { idleRef.current = true; return; }

      var tgt = targetRef.current;
      var anyMove = false;
      var tk = tickRef.current;

      for (var i = 0; i < BIN_COUNT; i++) {
        var t = tgt[i] || 0;
        var c = dataRef.current[i] || 0;
        var diff = t - c;
        if (Math.abs(diff) > 0.001) anyMove = true;
        dataRef.current[i] = c + diff * Math.min(1, (tk + 1) / 8);
      }

      drawFrame();
      tickRef.current = tk + 1;

      if (anyMove && tk < 15) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        for (var i = 0; i < BIN_COUNT; i++) dataRef.current[i] = tgt[i] || 0;
        drawFrame();
        idleRef.current = true;
        // Start gentle idle breathing at 5fps
        idleRAF();
      }
    }

    var idleRafRef = null;

    function idleRAF() {
      var count = 0;
      var maxIdle = 30; // 30 frames at 5fps = 6s then pause 2s
      function tick() {
        for (var i = 0; i < BIN_COUNT; i++) {
          var c = dataRef.current[i] || 0;
          var noise = (Math.random() - 0.5) * 0.01;
          dataRef.current[i] = Math.max(0, Math.min(1, c + noise));
        }
        drawFrame();
        count++;
        if (count < maxIdle) {
          idleRafRef = setTimeout(tick, 200);
        } else {
          idleRafRef = null;
        }
      }
      idleRafRef = setTimeout(tick, 200);
    }

    // Store kickstart function in the ref so render-phase code can call it
    kickRef.current = function() {
      // Cancel idle breathing when real data arrives
      if (idleRafRef !== null) { clearTimeout(idleRafRef); idleRafRef = null; }
      idleRef.current = false;
      if (rafRef.current === null) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    // Draw initial state
    drawFrame();

    // Start initial animation if we have signal
    if (hasSignal(targetRef.current)) {
      kickRef.current();
    }

    return function() {
      kickRef.current = null;
      if (idleRafRef !== null) { clearTimeout(idleRafRef); idleRafRef = null; }
      if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }
      idleRef.current = true;
      ro.disconnect();
    };
  }, []);

  var activeFft = fftData || {};
  var dataStale = (Date.now() - lastDataMs.current) > 15000;
  var displayFreq = dataStale ? null : activeFft.mpu_dom_freq;
  var displayAmp = dataStale ? null : activeFft.mpu_peak_amp;
  var displayPiezo = dataStale ? null : activeFft.piezo_dom_freq;
  // Decay canvas to flat when data is stale
  if (dataStale) {
    for (var i = 0; i < BIN_COUNT; i++) {
      targetRef.current[i] = 0.02;
    }
  }

  return React.createElement("div", {
    id: "fft-waveform-panel",
    className: "card-glass p-5 flex flex-col gap-2 transition-all duration-300 " + (isExpanded ? "fixed inset-[10%] z-50 bg-slate-950 shadow-2xl" : "h-full animate-slide-in relative")
  },
    React.createElement("div", { className: "flex items-center justify-between" },
      React.createElement("div", { className: "flex items-center gap-2" },
        React.createElement(Radio, { size: 14, strokeWidth: 1.5, style: { color: "#0ea5e9" } }),
        React.createElement("h2", { className: "text-xs font-semibold tracking-wider uppercase text-[var(--color-text-primary)]" }, "Live FFT Waveform"),
        React.createElement("span", { className: "relative flex h-2 w-2 ml-1" },
          React.createElement("span", { className: "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", style: { background: faultActive ? "#e11d48" : "#10b981" } }),
          React.createElement("span", { className: "relative inline-flex rounded-full h-2 w-2", style: { background: faultActive ? "#e11d48" : "#10b981" } })
        ),
        React.createElement("span", { className: "text-[9px] font-mono uppercase", style: { color: faultActive ? "#e11d48" : "#10b981" } }, "Live")
      ),
      React.createElement("div", { className: "flex items-center gap-3" },
        React.createElement("span", { className: "text-[9px] font-mono text-[var(--color-text-muted)]" },
          "MPU: " + (displayFreq ? displayFreq.toFixed(1) : "0") + "Hz @ " + (displayAmp ? displayAmp.toFixed(3) : "0.000") + "g"
        ),
        React.createElement("span", { className: "text-[9px] font-mono text-[var(--color-text-muted)]" },
          "Piezo: " + (displayPiezo ? displayPiezo.toFixed(0) : "0") + "Hz"
        ),
        React.createElement("button", {
          onClick: function() { setExpandedCard(isExpanded ? null : "fft"); },
          className: "p-1 rounded-sm hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
        },
          isExpanded
            ? React.createElement(Minimize2, { size: 12, strokeWidth: 1.5, className: "text-[var(--color-text-muted)]" })
            : React.createElement(Maximize2, { size: 12, strokeWidth: 1.5, className: "text-[var(--color-text-muted)]" })
        )
      )
    ),
    React.createElement("div", { className: "flex gap-1 p-0.5 rounded-sm", style: { background: "rgba(15,23,42,0.6)" } },
      TABS.map(function(tab, i) {
        var active = activeNode === i;
        return React.createElement("button", {
          key: tab,
          onClick: function() { if (onNodeChange) onNodeChange(i); },
          className: "flex-1 py-1 text-[11px] font-medium rounded-sm transition-all duration-200 cursor-pointer " + (active ? "text-[var(--color-text-primary)] font-semibold" : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"),
          style: active ? { background: "rgba(30,41,59,0.8)", border: "1px solid #334155" } : { border: "1px solid transparent" }
        }, tab);
      })
    ),
    React.createElement("div", { className: "flex-1 rounded border border-slate-800 overflow-hidden relative", style: { background: "#020617" } },
      React.createElement("canvas", { ref: canvasRef, className: "absolute inset-0 w-full h-full", style: { touchAction: "none" } })
    )
  );
}

export default React.memo(FFTWaveform);
