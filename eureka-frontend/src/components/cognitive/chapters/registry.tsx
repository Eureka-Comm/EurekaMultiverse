import type { ComponentType } from 'react';
import type { HeroProps } from './types';
import { OpenChapter } from './OpenChapter';
import { QuestionChapter } from './QuestionChapter';
import { ContextChapter } from './ContextChapter';
import { DiscoveryChapter } from './DiscoveryChapter';
import { PredictionChapter } from './PredictionChapter';
import { PrescriptionChapter } from './PrescriptionChapter';
import { DecisionChapter } from './DecisionChapter';
import { ActionChapter } from './ActionChapter';
import { ResultChapter } from './ResultChapter';

export type ChapterId =
  | 'open'
  | 'question'
  | 'context'
  | 'discovery'
  | 'prediction'
  | 'prescription'
  | 'decision'
  | 'action'
  | 'result';

export interface ChapterMeta {
  id: ChapterId;
  num: string;
  title: string;
  short: string;
  Component: ComponentType<HeroProps>;
}

export const CHAPTERS: ChapterMeta[] = [
  { id: 'open', num: '00', title: 'OPEN', short: 'What remains open', Component: OpenChapter },
  { id: 'question', num: '01', title: 'QUESTION', short: 'The cognitive framing', Component: QuestionChapter },
  { id: 'context', num: '02', title: 'CONTEXT', short: 'Metadata rails', Component: ContextChapter },
  { id: 'discovery', num: '03', title: 'DISCOVERY', short: 'Evidence & findings', Component: DiscoveryChapter },
  { id: 'prediction', num: '04', title: 'PREDICTION', short: 'Mathematical evaluation', Component: PredictionChapter },
  { id: 'prescription', num: '05', title: 'PRESCRIPTION', short: 'Alternatives & criteria', Component: PrescriptionChapter },
  { id: 'decision', num: '06', title: 'DECISION', short: 'Human decision field', Component: DecisionChapter },
  { id: 'action', num: '07', title: 'ACTION', short: 'Action lineage', Component: ActionChapter },
  { id: 'result', num: '08', title: 'RESULT', short: 'Outcome', Component: ResultChapter },
];

export const CHAPTER_BY_ID = Object.fromEntries(CHAPTERS.map((c) => [c.id, c])) as Record<ChapterId, ChapterMeta>;

function countFor(id: ChapterId, dto: any): number | null {
  switch (id) {
    case 'open': return dto.whatRemainsOpen?.items?.length ?? null;
    case 'discovery': return dto.findings?.length ?? null;
    case 'prediction': return dto.predictions?.length ?? null;
    case 'prescription': return dto.prescription?.alternatives?.length ?? null;
    default: return null;
  }
}

/** Small count badge shown next to a chapter in the navigator. */
export function chapterCount(id: ChapterId, dto: any): number | null {
  return countFor(id, dto);
}
