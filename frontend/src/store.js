import { create } from "zustand";

const INITIAL_NODES = {
  "Node A": { score: 100, readings: { accelX: "0.02g", accelY: "0.01g", piezo: "1.4V" } },
  "Node B": { score: 100, readings: { accelX: "0.04g", accelY: "0.03g", piezo: "2.1V" } },
  "Node C": { score: 100, readings: { accelX: "0.01g", accelY: "0.02g", piezo: "1.2V" } },
};

export const useStore = create((set, get) => ({
  nodes: INITIAL_NODES,
  events: [
    { id: "s1", time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "Telemetry stream connected — listening on ws://localhost:8080" },
    { id: "s2", time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "Sensors calibrated and baseline established" },
  ],
  activeNode: 0,
  wsConnected: false,
  healthHistory: [],
  expandedCard: null,

  setWsConnected: (connected) => set({ wsConnected: connected }),
  setActiveNode: (index) => set({ activeNode: index }),
  setExpandedCard: (id) => set({ expandedCard: id }),

  updateNode: (nodeName, data) => {
    set((state) => ({
      nodes: {
        ...state.nodes,
        [nodeName]: {
          ...state.nodes[nodeName],
          ...data,
          readings: {
            ...state.nodes[nodeName].readings,
            ...(data.readings || {}),
          },
        },
      },
    }));
  },

  addEvent: (event) => set((state) => ({ events: [event, ...state.events] })),

  setHealthHistory: (history) => set({ healthHistory: history }),

  reset: () => set({
    nodes: INITIAL_NODES,
    activeNode: 0,
    healthHistory: [],
    events: [
      { id: "reset-" + Date.now(), time: new Date().toLocaleTimeString("en-US", { hour12: false }), node: "System", level: "healthy", msg: "System Initialized — All clear" },
    ],
  }),
}));
