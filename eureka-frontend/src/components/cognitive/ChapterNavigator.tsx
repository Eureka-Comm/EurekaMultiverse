import React from 'react';
import type { ChapterId, ChapterMeta } from './chapters/registry';
import { chapterCount, CHAPTERS } from './chapters/registry';

/**
 * The CHAPTER TRAJECTORY — the cognitive timeline that carries the user through
 * the 8 cognitive states (01 QUESTION … 08 RESULT). It is a scientific
 * instrument's traversal rail, not a tab strip:
 *   · the base rail is the cognition thread;
 *   · the current cognitive state is the ACTIVE node (illuminated);
 *   · stages already traversed are marked "idle/done";
 *   · a stage with governed data is "live", without data is "empty" (honest).
 */
export function ChapterNavigator({
  chapters,
  active,
  onSelect,
  dto,
}: {
  chapters: ChapterMeta[];
  active: ChapterId;
  onSelect: (id: ChapterId) => void;
  dto: any;
}) {
  const activeIdx = chapters.findIndex((c) => c.id === active);
  const pct = chapters.length > 1 ? (activeIdx / (chapters.length - 1)) * 100 : 0;

  return (
    <nav className="ci-trajectory" aria-label="Cognitive chapter trajectory">
      <span className="ci-trajectory-progress" style={{ width: `${pct}%` }} />
      {chapters.map((c) => {
        const count = chapterCount(c.id, dto);
        const isActive = active === c.id;
        const idx = chapters.indexOf(c);
        const traversed = idx < activeIdx;
        const live = count != null && count > 0;
        const stateClass = isActive ? 'is-active' : traversed ? 'is-idle' : live ? 'is-live' : 'is-empty';
        return (
          <button
            key={c.id}
            className={`ci-traj-node ${stateClass}`}
            onClick={() => onSelect(c.id)}
            aria-current={isActive ? 'step' : undefined}
            title={c.short}
          >
            <span className="ci-traj-head">
              <span className="ci-traj-dot" />
              <span className="ci-traj-num">{c.num}</span>
            </span>
            <span className="ci-traj-label">{c.title}</span>
            {count != null && count > 0 && <span className="ci-traj-count">{count}</span>}
          </button>
        );
      })}
    </nav>
  );
}

export default ChapterNavigator;
