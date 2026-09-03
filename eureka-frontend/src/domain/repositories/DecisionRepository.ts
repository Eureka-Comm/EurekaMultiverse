import { type DecisionViewModel, type DecisionStage } from "../models";

export interface DecisionRepository {
  getDecision(id: string): Promise<DecisionViewModel | null>;
  listDecisions(): Promise<DecisionViewModel[]>;
  createDecision(title: string, initialPrompt: string): Promise<DecisionViewModel>;
  addAgentOutput(decisionId: string, content: string): Promise<DecisionViewModel>;
  evaluateDecision(decisionId: string): Promise<DecisionViewModel>;
  selectAlternative(decisionId: string, alternativeId: string): Promise<DecisionViewModel>;
  prescribeAction(decisionId: string): Promise<DecisionViewModel>;
  unfreeze(decisionId: string, signature: string): Promise<DecisionViewModel>;
  execute(decisionId: string): Promise<DecisionViewModel>;
}
