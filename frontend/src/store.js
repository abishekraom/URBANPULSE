import { create } from "zustand";
import { CANONICAL_NODE_NAMES } from "./nodeIdentity";

const MAX_EVENTS = 50;

const EMPTY_NODE = { score: 0, state: "WAITING", severity: "NORMAL", readings: { accelX: "—", accelY: "—", piezo: "—" }, fft: { mpu_dom_freq: 0, mpu_peak_amp: 0, mpu_centroid: 0, piezo_dom_freq: 0, piezo_peak_amp: 0, piezo_centroid: 0 } };

const createInitialNodes = () => Object.fromEntries(
  CANONICAL_NODE_NAMES.map((name) => [name, structuredClone(EMPTY_NODE)])
);

const INITIAL_NODES = createInitialNodes();

export const useStore = create((set) => ({
  nodes: INITIAL_NODES,
  events: [
    { id: "s1", time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "Dashboard initialized — waiting for telemetry..." },
  ],
  activeNode: 0,
  wsConnected: false,
  healthHistory: [],
  expandedCard: null,
  thresholds: null,

  setWsConnected: (connected) => set({ wsConnected: connected }),
  setActiveNode: (index) => set({ activeNode: index }),
  setExpandedCard: (id) => set({ expandedCard: id }),
  setThresholds: (thresholds) => set({ thresholds }),

  updateNode: (nodeName, data) => {
    if (!nodeName || !CANONICAL_NODE_NAMES.includes(nodeName)) return;
    set((state) => {
      const existing = state.nodes[nodeName] || EMPTY_NODE;
      return {
        nodes: {
          ...state.nodes,
          [nodeName]: {
            ...existing,
            ...data,
            readings: {
              ...existing.readings,
              ...(data.readings || {}),
            },
            fft: {
              ...existing.fft,
              ...(data.fft || {}),
            },
          },
        },
      };
    });
  },

  addEvent: (event) => set((state) => {
    const next = [event, ...state.events];
    if (next.length > MAX_EVENTS) next.length = MAX_EVENTS;
    return { events: next };
  }),

  setHealthHistory: (history) => set({ healthHistory: history }),

  reset: () => set({
    nodes: createInitialNodes(),
    activeNode: 0,
    healthHistory: [],
    events: [
      { id: "reset-" + Date.now(), time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "System reset" },
    ],
  }),
}));
