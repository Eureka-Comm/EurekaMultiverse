import React from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import type { CognitiveViewKey } from '../../../domain/cognitiveView';
import ViewWhySelected from './ViewWhySelected';
import ViewWhatUncertain from './ViewWhatUncertain';
import ViewWhatChanged from './ViewWhatChanged';
import ViewAlternativeLandscape from './ViewAlternativeLandscape';
import ViewEvaluation from './ViewEvaluation';
import ViewHumanAuthority from './ViewHumanAuthority';
import ViewOutcomeStory from './ViewOutcomeStory';
import CognitiveTimeline from './CognitiveTimeline';
import ViewGeneric from './ViewGeneric';
import ActionDependencyGraph from '../ActionDependencyGraph';

/**
 * Maps a CognitiveViewKey to the React component that ANSWERS its question.
 * This is the single render point that replaces the per-stage chart pipeline.
 */
export default function CognitiveViewRenderer({
  state,
  viewKey,
}: {
  state: CanonicalWorkState;
  viewKey: CognitiveViewKey;
}) {
  switch (viewKey) {
    case 'WHY_SELECTED':
      return <ViewWhySelected state={state} />;
    case 'WHAT_IS_UNCERTAIN':
      return <ViewWhatUncertain state={state} />;
    case 'WHAT_CHANGED':
      return <ViewWhatChanged state={state} />;
    case 'ALTERNATIVE_LANDSCAPE':
      return <ViewAlternativeLandscape state={state} />;
    case 'HUMAN_AUTHORITY':
      return <ViewHumanAuthority state={state} />;
    case 'OUTCOME_STORY':
      return <ViewOutcomeStory state={state} />;
    case 'WHAT_HAPPENED':
      return <CognitiveTimeline state={state} />;
    // ACTION_DAG: the operational explanation DAG (each action node exposes
    // What→Why→Who→Inputs→Expected Output→Evidence→Dependency→Status).
    case 'ACTION_DAG':
      return <ActionDependencyGraph state={state} detailed />;
    case 'EVALUATION':
      return <ViewEvaluation state={state} />;
    case 'QUESTION':
    case 'CONTEXT':
    case 'DATA':
    case 'DISCOVERY':
    case 'LEARNING':
    default:
      return <ViewGeneric state={state} viewKey={viewKey} />;
  }
}
