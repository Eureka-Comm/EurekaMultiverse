// EUREKA 5.1 — HUMAN INPUT submit contract (identity + single-flight).
//
// TEST 2 / TEST 5 / TEST 6: one click, one rerender or one StrictMode double-effect must produce
//                           EXACTLY ONE submission.
// TEST 7 (client side):      a request that names another work is refused before any POST.
// The auto-narration / viewer-question paths must NEVER be consumed as the human's answer (that is
// what posted the original QUESTION as the answer — the echo of production WORK-D120C202).
import { describe, it, expect, beforeEach } from 'vitest';
import {
  beginHumanSubmit, endHumanSubmit, isHumanSubmitInFlight, humanSubmitKey,
  shouldRouteToHumanGate, requestBelongsToWork,
} from './humanSubmit';

beforeEach(() => {
  endHumanSubmit('WORK-A', 'REQ-1');   // isolate cases (module-level registry)
  endHumanSubmit('WORK-A', 'REQ-2');
});

describe('beginHumanSubmit — single-flight (one click => one POST)', () => {
  it('grants the flight once and refuses the duplicate (double click / remount / StrictMode effect)', () => {
    expect(isHumanSubmitInFlight('WORK-A', 'REQ-1')).toBe(false);
    expect(beginHumanSubmit('WORK-A', 'REQ-1')).toBe(true);    // POST #1 owner
    expect(beginHumanSubmit('WORK-A', 'REQ-1')).toBe(false);   // duplicate -> dropped
    expect(beginHumanSubmit('WORK-A', 'REQ-1')).toBe(false);   // StrictMode second effect -> dropped
    endHumanSubmit('WORK-A', 'REQ-1');
    expect(beginHumanSubmit('WORK-A', 'REQ-1')).toBe(true);    // a NEW attempt is allowed afterwards
    endHumanSubmit('WORK-A', 'REQ-1');
  });

  it('keys the flight by (work, request): another work or another request is independent', () => {
    expect(beginHumanSubmit('WORK-A', 'REQ-1')).toBe(true);
    expect(beginHumanSubmit('WORK-A', 'REQ-2')).toBe(true);    // governed follow-up
    expect(beginHumanSubmit('WORK-B', 'REQ-1')).toBe(true);    // other work
    endHumanSubmit('WORK-A', 'REQ-1'); endHumanSubmit('WORK-A', 'REQ-2'); endHumanSubmit('WORK-B', 'REQ-1');
  });

  it('exposes a stable key for the (work, request) pair', () => {
    expect(humanSubmitKey('WORK-A', 'REQ-1')).toBe('WORK-A::REQ-1');
  });
});

describe('shouldRouteToHumanGate — only an EXPLICIT human answer may close the gate', () => {
  it('never routes auto-narration (mount auto-submit) into the HITL gate', () => {
    expect(shouldRouteToHumanGate({ asHumanAnswer: false }, true)).toBe(false);
    expect(shouldRouteToHumanGate(undefined, true)).toBe(false);   // the historic default = the bug
  });

  it('never routes a viewer question ("ask the copilot") into the HITL gate', () => {
    expect(shouldRouteToHumanGate({ asHumanAnswer: false }, true)).toBe(false);
  });

  it('routes an explicit user send only when a blocking request is actually open', () => {
    expect(shouldRouteToHumanGate({ asHumanAnswer: true }, true)).toBe(true);
    expect(shouldRouteToHumanGate({ asHumanAnswer: true }, false)).toBe(false);
  });
});

describe('requestBelongsToWork — fail closed on work identity drift', () => {
  it('accepts a request that belongs to the target work', () => {
    expect(requestBelongsToWork('WORK-A', 'WORK-A')).toBe(true);
  });

  it('refuses a request that names ANOTHER work (the production drift)', () => {
    expect(requestBelongsToWork('WORK-B39C51D1', 'WORK-8DD6B1D1')).toBe(false);
  });

  it('accepts a legacy request without work_id (the server validates containment)', () => {
    expect(requestBelongsToWork(undefined, 'WORK-A')).toBe(true);
    expect(requestBelongsToWork('', 'WORK-A')).toBe(true);
  });

  it('refuses when there is no target work at all', () => {
    expect(requestBelongsToWork('WORK-A', undefined)).toBe(false);
    expect(requestBelongsToWork('WORK-A', '')).toBe(false);
  });
});
