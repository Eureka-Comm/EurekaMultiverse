import React from 'react';
import type { HeroProps } from './types';
import { Kicker, Panel, Honest } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';

/**
 * 05 — PRESCRIPTION. The OPTION SPACE. Criteria are reference rails; each
 * alternative is an honest candidate in the space. RECOMMENDED (EM Prescriptor
 * candidate) and HUMAN (human_decision) are distinct markers — a candidate is
 * never shown as "selected" by the system. Reads ONLY from the single DTO
 * (no invented scores).
 */
export function PrescriptionChapter({ dto, onSelectArtifact, graph }: HeroProps) {
  const prescription = dto.prescription;
  const recommended = dto.recommendedOption;
  const humanSelection = dto.humanDecision.selectedAlternativeId;
  const alternatives = prescription?.alternatives || [];

  const artifactById = new Map(graph.nodes.map((n) => [n.id, n]));
  const selectAlternative = (id: string) => {
    const art = artifactById.get(id);
    if (art) onSelectArtifact(art);
  };
  const selectPrescription = () => {
    if (prescription?.id) {
      const art = artifactById.get(prescription.id);
      if (art) onSelectArtifact(art);
    }
  };

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="05" title="Prescription" sub="Option space" />
        {prescription && <AuthorityChip authority={prescription.authority} />}
      </div>

      {/* Criteria rails */}
      <Panel title="Evaluation criteria · EM Prescriptor" accent="var(--eureka-signal-cognitive)">
        {prescription?.criteria?.length ? (
          <div className="flex flex-wrap gap-2">
            {prescription.criteria.map((c, i) => (
              <span key={i} className="ci-tag-chip">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--eureka-signal-cognitive)]" />
                {c}
              </span>
            ))}
          </div>
        ) : (
          <div className="text-xs text-[var(--eureka-text-micro)]">No evaluation criteria recorded.</div>
        )}
      </Panel>

      {/* Candidate field */}
      <div className="flex-1">
        <div className="ci-field-label mb-2">
          Candidate field ({alternatives.length}) · recommended ≠ human selection
        </div>
        {alternatives.length ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {alternatives.map((a) => {
              const isRec = a.id === recommended;
              const isHum = a.id === humanSelection;
              return (
                <button
                  key={a.id}
                  onClick={() => selectAlternative(a.id)}
                  className="flex flex-col gap-2 border p-3 text-left transition-colors hover:border-[var(--eureka-signal-cognitive)]"
                  style={{ borderColor: isHum ? 'var(--eureka-signal-authority)' : 'var(--eureka-spatial-hairline)', borderWidth: isHum ? 1.5 : 1 }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[12px] font-bold text-[var(--eureka-text-display)]">{a.id}</span>
                    <div className="flex items-center gap-1.5">
                      {isRec && <span className="text-[9px] font-mono text-[var(--eureka-signal-cognitive)] border border-[var(--eureka-signal-cognitive)] rounded px-1 py-0.5">RECOMMENDED</span>}
                      {isHum && <AuthorityChip authority="HUMAN_AUTHORIZED" label="HUMAN" size="sm" />}
                    </div>
                  </div>
                  <div className="text-[11px] text-[var(--eureka-text-section)] leading-snug">{a.description}</div>
                  <div className="mt-auto flex items-center justify-between pt-1">
                    <span className="text-[9px] font-mono text-[var(--eureka-text-micro)]">candidate</span>
                    {isHum && <span className="text-[9px] font-mono text-[var(--eureka-signal-authority)]">human_decision</span>}
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <Honest label="DATA NOT AVAILABLE" tone="var(--eureka-text-technical)">No candidates proposed for this work.</Honest>
        )}
      </div>

      {/* Rationale */}
      {prescription?.rationale && (
        <div className="border-t border-[var(--eureka-spatial-hairline)] pt-3">
          <button onClick={selectPrescription} className="text-left w-full group">
            <div className="ci-field-label mb-1">Rationale · EM Prescriptor</div>
            <div className="text-[12px] text-[var(--eureka-text-section)] leading-relaxed group-hover:text-[var(--eureka-text-display)]">
              {prescription.rationale}
            </div>
          </button>
        </div>
      )}
    </div>
  );
}

export default PrescriptionChapter;
