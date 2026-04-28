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
import { useStore } from "./store";

const INITIAL_NODES = {
  "Node A": { score: 100, readings: { accelX: "0.02g", accelY: "0.01g", piezo: "1.4V" } },
  "Node B": { score: 100, readings: { accelX: "0.04g", accelY: "0.03g", piezo: "2.1V" } },
  "Node C": { score: 100, readings: { accelX: "0.01g", accelY: "0.02g", piezo: "1.2V" } },
};

const SEED_EVENTS = [
  { id: "s1", time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "Telemetry stream connecting via Vite proxy → ws://localhost:8000/ws" },
  { id: "s2", time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "Sensors calibrated and baseline established" },
];

function now() {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function deriveSystemStatus(nodes) {
  const scores = Object.values(nodes).map((n) => n.score);
  const min = Math.min(...scores);
  if (min < 40) return "critical";
  if (min < 80) return "warning";
  return "clear";
}

let eventCounter = 100;

export default function App() {
  const nodes = useStore((state) => state.nodes);
  const events = useStore((state) => state.events);
  const activeNode = useStore((state) => state.activeNode);
  const healthHistory = useStore((state) => state.healthHistory);
  const wsConnected = useStore((state) => state.wsConnected);
  
  const updateNode = useStore((state) => state.updateNode);
  const addEvent = useStore((state) => state.addEvent);
  const setWsConnected = useStore((state) => state.setWsConnected);
  const setActiveNode = useStore((state) => state.setActiveNode);
  const setHealthHistory = useStore((state) => state.setHealthHistory);
  const reset = useStore((state) => state.reset);

  const requestRef = useRef();

  // Map backend node_id ("A","B","C") → frontend node name ("Node A","Node B","Node C")
  const toNodeName = (id) => `Node ${id}`;

  // Format raw sensor values for display
  const formatReading = (payload) => ({
    accelX: payload?.mpu?.raw_x != null ? `${payload.mpu.raw_x.toFixed(3)}g` : "—",
    accelY: payload?.mpu?.raw_y != null ? `${Math.abs(payload.mpu.raw_y).toFixed(3)}g` : "—",
    piezo:  payload?.piezo?.raw_adc != null ? `${(payload.piezo.raw_adc / 410).toFixed(1)}V` : "—",
  });

  useEffect(() => {
    // Use relative URL so it routes through the Vite dev-server proxy (/ws → ws://localhost:8000/ws)
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws`;
    let ws;
    let pendingUpdates = {}; // keyed by nodeName, deduplicated

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
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "snapshot") {
            // Initial state dump from backend
            (msg.nodes || []).forEach((n) => {
              const nodeName = toNodeName(n.node_id);
              updateNode(nodeName, { score: n.last_health_score ?? 100 });
            });
            (msg.alerts || []).slice(0, 5).forEach((a) => {
              addEvent({
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
            pendingUpdates[nodeName] = {
              nodeName,
              score: d.health_score,
              readings: formatReading(d.payload),
            };

          } else if (msg.type === "alert") {
            const d = msg.data;
            addEvent({
              id: `alert-${d.ts}-${d.node_id}`,
              time: new Date(d.ts).toLocaleTimeString("en-US", { hour12: false }),
              node: toNodeName(d.node_id),
              level: d.severity === "CRITICAL" ? "critical" : "warning",
              msg: d.reason,
            });

          } else if (msg.type === "node_update") {
            const d = msg.data;
            const nodeName = toNodeName(d.node_id);
            updateNode(nodeName, { score: d.last_health_score ?? 100 });
          }
        } catch (e) {
          console.warn("WS parse error:", e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    };

    // RAF-based batch flusher — applies deduplicated updates each frame
    const processUpdates = () => {
      const keys = Object.keys(pendingUpdates);
      if (keys.length > 0) {
        keys.forEach((nodeName) => {
          const u = pendingUpdates[nodeName];
          updateNode(nodeName, { score: u.score, readings: u.readings });
        });
        pendingUpdates = {};
      }
      requestRef.current = requestAnimationFrame(processUpdates);
    };

    connect();
    requestRef.current = requestAnimationFrame(processUpdates);

    return () => {
      ws?.close();
      cancelAnimationFrame(requestRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const systemStatus = deriveSystemStatus(nodes);
  const faultActive = Object.values(nodes).some(n => n.score < 40);

  const nodeScores = {};
  Object.entries(nodes).forEach(([name, data]) => {
    nodeScores[name] = data.score;
  });

  useEffect(() => {
    let lastTime = Date.now();
    const updateHistory = () => {
      const nowTime = Date.now();
      if (nowTime - lastTime >= 1000) {
        const currentNodes = useStore.getState().nodes;
        const newData = {
          time: now(),
          "Node A": currentNodes["Node A"].score,
          "Node B": currentNodes["Node B"].score,
          "Node C": currentNodes["Node C"].score,
        };
        const currentHistory = useStore.getState().healthHistory;
        setHealthHistory([...currentHistory.slice(-29), newData]);
        lastTime = nowTime;
      }
      requestRef.current = requestAnimationFrame(updateHistory);
    };
    
    const frameId = requestAnimationFrame(updateHistory);
    return () => cancelAnimationFrame(frameId);
  }, []);

  const simulateAlert = useCallback(() => {
    eventCounter++;
    const targetNodes = ["Node A", "Node B", "Node C"];
    const targetNode = targetNodes[Math.floor(Math.random() * targetNodes.length)];
    const nodeIndex = targetNodes.indexOf(targetNode);
    updateNode(targetNode, {
      score: 35,
      readings: { accelX: "0.87g", accelY: "0.85g", piezo: "4.5V" },
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
              readings={data.readings}
            />
          ))}
        </section>

        <section id="middle-row" className="flex-[1.5] grid grid-cols-5 gap-2 min-h-0">
          <div className="col-span-3 min-h-0">
            <FFTWaveform
              activeNode={activeNode}
              onNodeChange={setActiveNode}
              faultActive={nodes[["Node A", "Node B", "Node C"][activeNode]].score < 40}
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
        <Footer wsConnected={wsConnected} />

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
