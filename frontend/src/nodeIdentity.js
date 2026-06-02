export const CANONICAL_NODE_IDS = ['1', '2', '3'];
export const CANONICAL_NODE_NAMES = CANONICAL_NODE_IDS.map((id) => `Node ${id}`);

const LEGACY_NODE_ID_MAP = {
  A: '1',
  B: '2',
  C: '3',
};

const DISPLAY_LABELS = {
  '1': 'Node A',
  '2': 'Node B',
  '3': 'Node C',
};

export function normalizeNodeId(input) {
  if (input == null) return null;
  let value = String(input).trim();
  if (!value) return null;

  if (/^node\s+/i.test(value)) {
    value = value.replace(/^node\s+/i, '').trim();
  }

  value = value.toUpperCase();
  const mapped = LEGACY_NODE_ID_MAP[value] || value;
  return CANONICAL_NODE_IDS.includes(mapped) ? mapped : null;
}

export function toNodeName(input) {
  const id = normalizeNodeId(input);
  return id ? `Node ${id}` : null;
}

export function toNodeIndex(input) {
  const id = normalizeNodeId(input);
  return id ? CANONICAL_NODE_IDS.indexOf(id) : -1;
}

export function toDisplayNodeLabel(input) {
  const id = normalizeNodeId(input);
  return id ? DISPLAY_LABELS[id] : 'Unknown Node';
}
