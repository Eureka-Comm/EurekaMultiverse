import { describe, it, expect, afterEach } from 'vitest';
import { detectGpuBackend } from './CognitiveField';

/**
 * LS93 v6 — Defecto 2 honesty fix. `detectGpuBackend()` must report the backend
 * that ACTUALLY renders. The regression this test pins: a WebGL1-only browser was
 * previously labeled 'webgl2' because the `getContext('webgl')` fallback branch
 * returned 'webgl2'. Probe with a controlled canvas stub (node env, no real GL).
 */
function stubDocument(getContextReturn: (type: string) => unknown) {
  const canvas = { getContext: (type: string) => getContextReturn(type) } as unknown;
  (globalThis as any).document = {
    createElement: (tag: string) => (tag === 'canvas' ? canvas : {}),
  };
}

describe('detectGpuBackend — honest backend probe (LS93 v6)', () => {
  afterEach(() => {
    delete (globalThis as any).document;
  });

  it('WebGL2-capable browser -> reports "webgl2"', async () => {
    stubDocument((t) => (t === 'webgl2' ? {} : null));
    await expect(detectGpuBackend()).resolves.toBe('webgl2');
  });

  it('WebGL1-only browser -> reports "webgl1" (the REAL backend), never "webgl2"', async () => {
    stubDocument((t) => (t === 'webgl' ? {} : null));
    await expect(detectGpuBackend()).resolves.toBe('webgl1');
  });

  it('WebGL1-only (webgl present, webgl2 absent) is NOT mislabeled as webgl2', async () => {
    stubDocument((t) => (t === 'webgl2' ? null : t === 'webgl' ? {} : null));
    await expect(detectGpuBackend()).resolves.toBe('webgl1');
  });

  it('no WebGL context at all -> reports "none" (DOM/SVG fallback)', async () => {
    stubDocument(() => null);
    await expect(detectGpuBackend()).resolves.toBe('none');
  });
});
