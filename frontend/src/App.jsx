import { useState, useCallback, useEffect, useRef } from "react";
import StatusBanner from "./components/StatusBanner";
import NodeCard from "./components/NodeCard";
import FFTWaveform from "./components/FFTWaveform";
import StructuralMap from "./components/StructuralMap";
import AlertTimeline from "./components/AlertTimeline";
import Footer from "./components/Footer";
import HistoricalChart from "./components/HistoricalChart";
import RawDataGrid from "./components/RawDataGrid";
import { Zap, RotateCcw } from "lucide-react";
import { shallow } from "zustand/shallow";
import { useStore } from "./store";

function now() {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function deriveSystemStatus(nodes) {
  const values = Object.values(nodes);
  // If any node is waiting, show initializing
  if (values.some((n) => n.state === "WAITING")) return "clear";
  const scores = values.map((n) => n.score);
  const min = Math.min(...scores);
  if (min < 40) return "critical";
  if (min < 80) return "warning";
  return "clear";
}

let eventCounter = 100;

export default function App() {
  const nodes = useStore((state) => state.nodes, shallow);
  const events = useStore((state) => state.events, shallow);
  const activeNode = useStore((state) => state.activeNode);
  const healthHistory = useStore((state) => state.healthHistory, shallow);
  const wsConnected = useStore((state) => state.wsConnected);
  const thresholds = useStore((state) => state.thresholds);

  const updateNode = useStore((state) => state.updateNode);
  const addEvent = useStore((state) => state.addEvent);
  const setWsConnected = useStore((state) => state.setWsConnected);
  const setActiveNode = useStore((state) => state.setActiveNode);
  const setHealthHistory = useStore((state) => state.setHealthHistory);
  const setThresholds = useStore((state) => state.setThresholds);
  const reset = useStore((state) => state.reset);

  const historyIntervalRef = useRef();

  // Map backend node_id ("A","B","C") → frontend node name ("Node A","Node B","Node C")
  const toNodeName = (id) => `Node ${id}`;

  // Format raw sensor values for display — use RMS from firmware when raw values are 0
  const formatReading = (payload) => ({
    accelX: payload?.mpu?.raw_x != null && payload.mpu.raw_x !== 0 ? `${payload.mpu.raw_x.toFixed(3)}g` : 
            payload?.mpu?.rms != null ? `${payload.mpu.rms.toFixed(3)}g` : "—",
    accelY: payload?.mpu?.raw_y != null && payload.mpu.raw_y !== 0 ? `${Math.abs(payload.mpu.raw_y).toFixed(3)}g` : "—",
    piezo:  payload?.piezo?.raw_adc != null && payload.piezo.raw_adc !== 0 ? `${(payload.piezo.raw_adc / 410).toFixed(1)}V` : 
            payload?.piezo?.rms != null ? `${(payload.piezo.rms * 3.3).toFixed(2)}V` : "—",
  });

  // Extract FFT features from payload for the waveform visualization
  const extractFFT = (payload) => ({
    mpu_dom_freq: payload?.mpu?.dom_freq ?? 0,
    mpu_peak_amp: payload?.mpu?.peak_amp ?? 0,
    mpu_centroid: payload?.mpu?.spectral_centroid ?? 0,
    piezo_dom_freq: payload?.piezo?.dom_freq ?? 0,
    piezo_peak_amp: payload?.piezo?.peak_amp ?? 0,
    piezo_centroid: payload?.piezo?.spectral_centroid ?? 0,
  });

  // ── Fetch thresholds from backend on mount ──
  useEffect(() => {
    fetch("/api/config/thresholds")
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setThresholds(data); })
      .catch(() => {});
  }, [setThresholds]);

  // ── Fetch health history from REST API every 10s (reduced from 5s) ──
  useEffect(() => {
    const NODE_IDS = ["1", "2", "3"];
    const NODE_NAMES = ["Node 1", "Node 2", "Node 3"];

    // Track last fetch timestamp to throttle
    let lastFetch = 0;

    const fetchHistory = async (force) => {
      // Throttle: don't fetch more than once per 5s (for browser idle)
      const now = Date.now();
      if (!force && now - lastFetch < 5000) return;
      lastFetch = now;

      try {
        const allRaw = [];
        for (let i = 0; i < NODE_IDS.length; i++) {
          const res = await fetch(`/api/nodes/${NODE_IDS[i]}/history?minutes=10`);
          if (!res.ok) continue;
          const data = await res.json();
          data.forEach((pt) => {
            allRaw.push({ ts: pt.ts, nodeName: NODE_NAMES[i], score: pt.score });
          });
        }
        if (allRaw.length > 0) {
          allRaw.sort((a, b) => a.ts - b.ts);
          const BUCKET_MS = 6000;
          const buckets = {};
          allRaw.forEach((pt) => {
            const bucketKey = Math.floor(pt.ts / BUCKET_MS) * BUCKET_MS;
            if (!buckets[bucketKey]) {
              buckets[bucketKey] = { time: new Date(bucketKey).toLocaleTimeString("en-US", { hour12: false }) };
            }
            buckets[bucketKey][pt.nodeName] = pt.score;
          });
          const merged = Object.values(buckets).slice(-60);
          setHealthHistory(merged);
        }
      } catch {
        // Backend not ready yet
      }
    };

    fetchHistory(true);
    const interval = setInterval(() => fetchHistory(false), 10000);
    return () => clearInterval(interval);
  }, [setHealthHistory]);

  // ── WebSocket connection with RAF-based throttle (30fps cap) ──
  useEffect(() => {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws`;
    let ws;
    let pendingUpdates = {};
    let pendingAlerts = [];
    let rafId = null;
    let lastFlushTime = 0;
    const FLUSH_INTERVAL_MS = 33; // ~30fps

    // RAF-based flusher — only runs while tab is visible
    const RAF_THROTTLE = 33; // ms between flushes

    const flush = (timestamp) => {
      rafId = requestAnimationFrame(flush);

      const elapsed = timestamp - lastFlushTime;
      if (elapsed < RAF_THROTTLE) return; // throttle

      lastFlushTime = timestamp;

      // Flush pending node updates
      const keys = Object.keys(pendingUpdates);
      if (keys.length > 0) {
        const currentNodes = useStore.getState().nodes;
        keys.forEach((nodeName) => {
          const u = pendingUpdates[nodeName];
          const cur = currentNodes[nodeName];
          // Skip if nothing actually changed
          if (cur && cur.score === u.score && cur.severity === u.severity) return;
          updateNode(nodeName, { score: u.score, severity: u.severity, readings: u.readings, fft: u.fft });
        });
        pendingUpdates = {};
      }

      // Flush pending alerts (one per frame max to avoid layout thrash)
      if (pendingAlerts.length > 0) {
        const alert = pendingAlerts.shift();
        addEvent(alert);
      }
    };

    const connect = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        addEvent({
          id: `conn-${Date.now()}`,
          time: now(),
          node: "System",
          level: "healthy",
          msg: `WebSocket connected → ws://localhost:8000/ws (via Vite proxy)`,
        });
        // Start RAF flusher
        lastFlushTime = performance.now();
        rafId = requestAnimationFrame(flush);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "snapshot") {
            // Initial state dump — apply directly, batch in next RAF
            const curNodes = useStore.getState().nodes;
            (msg.nodes || []).forEach((n) => {
              const nodeName = toNodeName(n.node_id);
              const existingState = curNodes[nodeName]?.state;
              if (existingState === "WAITING") {
                setTimeout(() => {
                  updateNode(nodeName, { score: n.last_health_score ?? 100, state: n.state ?? "ONLINE", severity: "NORMAL" });
                }, 1500);
              } else {
                pendingUpdates[nodeName] = {
                  score: n.last_health_score ?? 100,
                  severity: "NORMAL",
                  readings: formatReading({}),
                  fft: extractFFT({}),
                };
              }
            });
            (msg.alerts || []).slice(0, 5).forEach((a) => {
              pendingAlerts.push({
                id: `snap-alert-${a.id}`,
                time: new Date(a.ts).toLocaleTimeString("en-US", { hour12: false }),
                node: toNodeName(a.node_id),
                level: a.severity === "CRITICAL" ? "critical" : "warning",
                msg: a.reason,
              });
            });

          } else if (msg.type === "reading") {
            const d = msg.data;
            const nodeName = toNodeName(d.node_id);

            // Backend now throttles to ~30fps, but we still use RAF
            // to decouple React renders from WebSocket message rate
            if (!pendingUpdates[nodeName]) {
              pendingUpdates[nodeName] = {};
            }
            pendingUpdates[nodeName] = {
              score: d.health_score,
              severity: d.severity,
              readings: formatReading(d.payload),
              fft: extractFFT(d.payload),
            };

          } else if (msg.type === "alert") {
            const d = msg.data;
            pendingAlerts.push({
              id: `alert-${d.ts}-${d.node_id}`,
              time: new Date(d.ts).toLocaleTimeString("en-US", { hour12: false }),
              node: toNodeName(d.node_id),
              level: d.severity === "CRITICAL" ? "critical" : "warning",
              msg: d.reason,
            });

          } else if (msg.type === "node_update") {
            const d = msg.data;
            const nodeName = toNodeName(d.node_id);
            // node_update is rare — apply directly
            updateNode(nodeName, {
              state: d.state,
              severity: d.state === "ONLINE" ? "NORMAL" : undefined,
              score: d.state === "ONLINE" ? (d.last_health_score ?? 100) : undefined,
            });
          }
        } catch (e) {
          console.warn("WS parse error:", e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (rafId) cancelAnimationFrame(rafId);
        setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      ws?.close();
      if (rafId) cancelAnimationFrame(rafId);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const systemStatus = deriveSystemStatus(nodes);
  const faultActive = Object.values(nodes).some(n => n.state === "ONLINE" && n.score < 40);

  const nodeNames = ["Node 1", "Node 2", "Node 3"];
  const nodeScores = {};
  Object.entries(nodes).forEach(([name, data]) => {
    nodeScores[name] = data.score;
  });

  const simulateAlert = useCallback(() => {
    eventCounter++;
    const targetNode = nodeNames[Math.floor(Math.random() * nodeNames.length)];
    const nodeIndex = nodeNames.indexOf(targetNode);
    updateNode(targetNode, {
      state: "ONLINE",
      score: 35,
      readings: { accelX: "0.87g", accelY: "0.85g", piezo: "4.5V" },
      fft: { mpu_dom_freq: 18.0, mpu_peak_amp: 0.85, mpu_centroid: 25.0, piezo_dom_freq: 480, piezo_peak_amp: 2500, piezo_centroid: 580 },
    });
    addEvent({
      id: `sim-${eventCounter}`,
      time: now(),
      node: targetNode,
      level: "critical",
      msg: "Anomaly detected — harmonic shift at 120Hz · bolt loosening suspected",
    });
    setActiveNode(nodeIndex);
  }, [updateNode, addEvent, setActiveNode]);

  return (
    <div className={`h-screen flex flex-col bg-[var(--color-bg-primary)] overflow-hidden transition-all duration-700`}>
      <StatusBanner systemStatus={systemStatus} />

      <main className="flex-1 flex flex-col gap-2 p-2 min-h-0">
        <section id="node-row" className="grid grid-cols-3 gap-2 flex-shrink-0">
          {Object.entries(nodes).map(([name, data]) => (
            <NodeCard
              key={name}
              name={name}
              score={data.score}
              state={data.state}
              severity={data.severity}
              readings={data.readings}
            />
          ))}
        </section>

        <section id="middle-row" className="flex-[1.5] grid grid-cols-5 gap-2 min-h-0">
          <div className="col-span-3 min-h-0">
            <FFTWaveform
              activeNode={activeNode}
              onNodeChange={setActiveNode}
              faultActive={nodes[nodeNames[activeNode]].score < 40}
              fftData={nodes[nodeNames[activeNode]].fft}
              thresholds={thresholds}
            />
          </div>
          <div className="col-span-2 min-h-0">
            <HistoricalChart data={healthHistory} />
          </div>
        </section>

        <section id="bottom-row" className="flex-1 grid grid-cols-10 gap-2 min-h-0">
          <div className="col-span-3 min-h-0">
            <StructuralMap activeNode={activeNode} nodeScores={nodeScores} />
          </div>
          <div className="col-span-4 min-h-0">
            <RawDataGrid nodes={nodes} />
          </div>
          <div className="col-span-3 min-h-0">
            <AlertTimeline events={events} />
          </div>
        </section>
      </main>

      <footer
        id="dashboard-footer"
        className="w-full px-4 py-2 flex items-center justify-between"
        style={{
          background: "rgba(15,23,42,0.8)",
          borderTop: "1px solid #334155",
        }}
      >
        <Footer wsConnected={wsConnected} nodes={nodes} />

        <div className="flex items-center gap-2">
          <button
            id="btn-simulate-alert"
            onClick={simulateAlert}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-[11px] font-mono font-semibold uppercase tracking-wider cursor-pointer transition-all duration-200 hover:scale-[1.02]"
            style={{
              background: "rgba(225,29,72,0.15)",
              border: "1px solid rgba(225,29,72,0.3)",
              color: "#e11d48",
            }}
          >
            <Zap size={12} strokeWidth={1.5} />
            Simulate Alert
          </button>
          <button
            id="btn-reset"
            onClick={reset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-[11px] font-mono font-semibold uppercase tracking-wider cursor-pointer transition-all duration-200 hover:scale-[1.02]"
            style={{
              background: "rgba(16,185,129,0.1)",
              border: "1px solid rgba(16,185,129,0.25)",
              color: "#10b981",
            }}
          >
            <RotateCcw size={12} strokeWidth={1.5} />
            Reset
          </button>
        </div>
      </footer>
    </div>
  );
}
