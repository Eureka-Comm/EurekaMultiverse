import { type DecisionRepository } from "../../domain/repositories/DecisionRepository";
import { type DecisionViewModel } from "../../domain/models";

const dummyDecision: DecisionViewModel = {
  id: "case-001",
  title: "Q4 European Expansion Strategy",
  status: "RANKED",
  createdAt: new Date(Date.now() - 86400000).toISOString(),
  updatedAt: new Date().toISOString(),
  alternatives: [
    { id: "alt-A", name: "Aggressive Launch (Berlin & Paris)", description: "Launch in both major cities simultaneously with heavy marketing.", data: { cost: 500000, expectedROI: 1.5, risk: 0.8 } },
    { id: "alt-B", name: "Phased Entry (Berlin First)", description: "Launch in Berlin, stabilize, then expand to Paris.", data: { cost: 250000, expectedROI: 1.2, risk: 0.4 } },
    { id: "alt-C", name: "Partnership Model", description: "Enter via joint venture with local distributors.", data: { cost: 100000, expectedROI: 1.1, risk: 0.2 } }
  ],
  objective: {
    id: "pred-001",
    expression: "Maximize(ROI) AND Risk < 0.5",
    variables: [
      { id: "v1", name: "ROI", type: "float" },
      { id: "v2", name: "Risk", type: "float" }
    ],
    sourceAuthority: "SYSTEM",
    provenance: "EUREKA Core Compiler",
    semanticAuthorityStatus: "VALIDATED"
  },
  agentOutputs: [
    {
      id: "out-1",
      provider: "Mock",
      runtime: "LOCAL",
      trust: "UNTRUSTED",
      authority: "NONE",
      content: "Based on the provided documents, I propose evaluating three alternatives: Aggressive Launch, Phased Entry, and Partnership Model. The objective should be maximizing ROI while keeping risk under 0.5.",
      timestamp: new Date(Date.now() - 80000000).toISOString(),
      proposedInterpretation: "Maximize(ROI) AND Risk < 0.5"
    }
  ],
  ranking: {
    id: "rank-001",
    predicateId: "pred-001",
    generatedAt: new Date(Date.now() - 3600000).toISOString(),
    sortedEvaluations: [
      { alternativeId: "alt-B", truthValue: 1.0, utility: 1.2, evidence: ["Risk is 0.4 (< 0.5)", "ROI is acceptable"] },
      { alternativeId: "alt-C", truthValue: 1.0, utility: 1.1, evidence: ["Risk is 0.2 (< 0.5)", "ROI is acceptable but lower"] },
      { alternativeId: "alt-A", truthValue: 0.0, utility: 0.0, evidence: ["Risk is 0.8 (Violates Risk < 0.5)", "Automatically rejected"] }
    ]
  },
  timeline: [
    { id: "t1", timestamp: new Date(Date.now() - 86400000).toISOString(), stage: "INPUT", actor: "USER", description: "Created case", state: "INFO" },
    { id: "t2", timestamp: new Date(Date.now() - 80000000).toISOString(), stage: "COGNITION", actor: "MOCK_AGENT", description: "Proposed objective and alternatives", state: "INFO" },
    { id: "t3", timestamp: new Date(Date.now() - 79000000).toISOString(), stage: "SEMANTIC", actor: "EUREKA_CORE", description: "Validated Objective Predicate", state: "SUCCESS" },
    { id: "t4", timestamp: new Date(Date.now() - 3600000).toISOString(), stage: "EVALUATION", actor: "SCIENTIFIC_FOUNDATION", description: "Generated ranking (Alt B wins)", state: "SUCCESS" }
  ]
};

export class DemoDecisionRepository implements DecisionRepository {
  private decisions = new Map<string, DecisionViewModel>();

  constructor() {
    this.decisions.set(dummyDecision.id, dummyDecision);
  }

  async getDecision(id: string): Promise<DecisionViewModel | null> {
    return this.decisions.get(id) || null;
  }

  async listDecisions(): Promise<DecisionViewModel[]> {
    return Array.from(this.decisions.values());
  }

  async createDecision(title: string, initialPrompt: string): Promise<DecisionViewModel> {
    const id = `case-${Date.now()}`;
    const newDec: DecisionViewModel = {
      id,
      title,
      status: "DRAFT",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      agentOutputs: [],
      alternatives: [],
      timeline: [{ id: `t-${Date.now()}`, timestamp: new Date().toISOString(), stage: "INPUT", actor: "USER", description: `Created case: ${initialPrompt}`, state: "INFO" }]
    };
    this.decisions.set(id, newDec);
    return newDec;
  }

  async addAgentOutput(decisionId: string, content: string): Promise<DecisionViewModel> {
    const dec = await this.getDecision(decisionId);
    if (!dec) throw new Error("Not found");
    
    dec.agentOutputs.push({
      id: `out-${Date.now()}`,
      provider: "DeepSeek",
      runtime: "LOCAL",
      trust: "UNTRUSTED",
      authority: "NONE",
      content,
      timestamp: new Date().toISOString()
    });
    dec.timeline.push({ id: `t-${Date.now()}`, timestamp: new Date().toISOString(), stage: "COGNITION", actor: "AGENT", description: "Agent proposed new output", state: "INFO" });
    dec.status = "ANALYZING";
    dec.updatedAt = new Date().toISOString();
    return dec;
  }

  async evaluateDecision(decisionId: string): Promise<DecisionViewModel> {
    const dec = await this.getDecision(decisionId);
    if (!dec) throw new Error("Not found");
    // In a real adapter, this calls the backend. Here we just mock the state transition.
    dec.status = "RANKED";
    dec.updatedAt = new Date().toISOString();
    return dec;
  }

  async selectAlternative(decisionId: string, alternativeId: string): Promise<DecisionViewModel> {
    const dec = await this.getDecision(decisionId);
    if (!dec) throw new Error("Not found");
    dec.status = "PRESCRIBED";
    dec.timeline.push({ id: `t-${Date.now()}`, timestamp: new Date().toISOString(), stage: "SELECTION", actor: "HUMAN_EXTERNAL", description: `Selected alternative ${alternativeId}`, state: "SUCCESS" });
    dec.updatedAt = new Date().toISOString();
    return this.prescribeAction(decisionId);
  }

  async prescribeAction(decisionId: string): Promise<DecisionViewModel> {
    const dec = await this.getDecision(decisionId);
    if (!dec) throw new Error("Not found");
    dec.prescription = {
      id: `rx-${Date.now()}`,
      decisionId,
      proposedAction: "Execute deployment scripts for selected alternative",
      target: "System Infrastructure",
      expectedEffect: "New resources provisioned",
      authorityStatus: { type: "HUMAN_EXTERNAL", status: "PENDING", provenance: "Selection View" }
    };
    dec.frozenArtifact = {
      id: `frz-${Date.now()}`,
      prescriptionId: dec.prescription.id,
      snapshot: { ...dec.prescription },
      frozenAt: new Date().toISOString(),
      status: "FROZEN",
      waitingFor: "HUMAN_EXTERNAL"
    };
    dec.status = "FROZEN";
    dec.timeline.push({ id: `t-${Date.now()}`, timestamp: new Date().toISOString(), stage: "FREEZE", actor: "EUREKA_CORE", description: "Prescription Frozen. Awaiting Authority.", state: "WARNING" });
    dec.updatedAt = new Date().toISOString();
    return dec;
  }

  async unfreeze(decisionId: string, signature: string): Promise<DecisionViewModel> {
    const dec = await this.getDecision(decisionId);
    if (!dec || !dec.frozenArtifact) throw new Error("Not found or not frozen");
    dec.frozenArtifact.status = "UNFROZEN";
    dec.executionAuthority = {
      status: "AUTHORIZED",
      gateReason: "Valid HUMAN_EXTERNAL signature provided",
      authorizedBy: signature,
      authorizedAt: new Date().toISOString()
    };
    dec.status = "AUTHORIZED";
    dec.timeline.push({ id: `t-${Date.now()}`, timestamp: new Date().toISOString(), stage: "UNFREEZE", actor: "HUMAN_EXTERNAL", description: "Signature validated. Unfrozen.", state: "SUCCESS" });
    dec.updatedAt = new Date().toISOString();
    return dec;
  }

  async execute(decisionId: string): Promise<DecisionViewModel> {
    const dec = await this.getDecision(decisionId);
    if (!dec || dec.status !== "AUTHORIZED") throw new Error("Not authorized for execution");
    dec.status = "EXECUTED";
    dec.timeline.push({ id: `t-${Date.now()}`, timestamp: new Date().toISOString(), stage: "ACTIONER", actor: "EUREKA_ACTIONER", description: "Action executed successfully.", state: "SUCCESS" });
    dec.updatedAt = new Date().toISOString();
    return dec;
  }
}
