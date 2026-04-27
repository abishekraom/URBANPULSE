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
  { id: "s1", time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "Telemetry stream connected — listening on ws://localhost:8080" },
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

  useEffect(() => {
    const wsUrl = "ws://localhost:8080";
    let ws;
    let pendingUpdates = [];

    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => setWsConnected(true);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.node) {
            pendingUpdates.push(data);
          }
        } catch (e) {}
      };
      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    };

    const processUpdates = () => {
      if (pendingUpdates.length > 0) {
        const latestUpdates = {};
        pendingUpdates.forEach(update => {
          latestUpdates[update.node] = update;
        });
        
        Object.values(latestUpdates).forEach(update => {
          updateNode(update.node, {
            score: update.score,
            readings: {
              accelX: update.accelX,
              accelY: update.accelY,
              piezo: update.piezo,
            }
          });
          
          const accelXEl = document.getElementById(`${update.node}-accelX`);
          const accelYEl = document.getElementById(`${update.node}-accelY`);
          const piezoEl = document.getElementById(`${update.node}-piezo`);
          
          if (accelXEl) accelXEl.innerText = update.accelX;
          if (accelYEl) accelYEl.innerText = update.accelY;
          if (piezoEl) piezoEl.innerText = update.piezo;
        });
        
        pendingUpdates = [];
      }
      requestRef.current = requestAnimationFrame(processUpdates);
    };

    connect();
    requestRef.current = requestAnimationFrame(processUpdates);

    return () => {
      ws?.close();
      cancelAnimationFrame(requestRef.current);
    };
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
