import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  CANONICAL_NODE_IDS,
  CANONICAL_NODE_NAMES,
  normalizeNodeId,
  toNodeName,
  toNodeIndex,
  toDisplayNodeLabel,
} from './nodeIdentity.js';

describe('node identity contract', () => {
  it('uses firmware/backend numeric IDs as canonical frontend nodes', () => {
    assert.deepEqual(CANONICAL_NODE_IDS, ['1', '2', '3']);
    assert.deepEqual(CANONICAL_NODE_NAMES, ['Node 1', 'Node 2', 'Node 3']);
  });

  it('normalizes numeric, prefixed, and legacy A/B/C node identifiers without creating extra store keys', () => {
    const cases = [
      [1, 'Node 1'],
      ['1', 'Node 1'],
      ['Node 1', 'Node 1'],
      ['A', 'Node 1'],
      ['Node A', 'Node 1'],
      [2, 'Node 2'],
      ['B', 'Node 2'],
      ['Node C', 'Node 3'],
    ];
    for (const [input, expected] of cases) {
      assert.equal(toNodeName(input), expected);
    }
  });

  it('returns stable indices and display labels for the dashboard map/FFT tabs', () => {
    assert.equal(toNodeIndex('1'), 0);
    assert.equal(toNodeIndex('Node B'), 1);
    assert.equal(toNodeIndex('C'), 2);
    assert.equal(toDisplayNodeLabel('Node 1'), 'Node A');
    assert.equal(toDisplayNodeLabel('2'), 'Node B');
    assert.equal(toDisplayNodeLabel('C'), 'Node C');
  });

  it('rejects unknown node identifiers instead of silently adding Node undefined-style keys', () => {
    assert.equal(normalizeNodeId('Z'), null);
    assert.equal(toNodeName('Z'), null);
    assert.equal(toNodeIndex('Z'), -1);
  });
});
