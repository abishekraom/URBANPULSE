import { create } from "zustand";

const INITIAL_NODES = {
  "Node 1": { score: 0, state: "WAITING", severity: "NORMAL", readings: { accelX: "—", accelY: "—", piezo: "—" }, fft: { mpu_dom_freq: 0, mpu_peak_amp: 0, mpu_centroid: 0, piezo_dom_freq: 0, piezo_peak_amp: 0, piezo_centroid: 0 } },
  "Node 2": { score: 0, state: "WAITING", severity: "NORMAL", readings: { accelX: "—", accelY: "—", piezo: "—" }, fft: { mpu_dom_freq: 0, mpu_peak_amp: 0, mpu_centroid: 0, piezo_dom_freq: 0, piezo_peak_amp: 0, piezo_centroid: 0 } },
  "Node 3": { score: 0, state: "WAITING", severity: "NORMAL", readings: { accelX: "—", accelY: "—", piezo: "—" }, fft: { mpu_dom_freq: 0, mpu_peak_amp: 0, mpu_centroid: 0, piezo_dom_freq: 0, piezo_peak_amp: 0, piezo_centroid: 0 } },
};

export const useStore = create((set, get) => ({
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
    set((state) => {
      const existing = state.nodes[nodeName] || INITIAL_NODES["Node 1"];
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

  addEvent: (event) => set((state) => ({ events: [event, ...state.events] })),

  setHealthHistory: (history) => set({ healthHistory: history }),

  reset: () => set({
    nodes: INITIAL_NODES,
    activeNode: 0,
    healthHistory: [],
    events: [
      { id: "reset-" + Date.now(), time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "System reset" },
    ],
  }),
}));
