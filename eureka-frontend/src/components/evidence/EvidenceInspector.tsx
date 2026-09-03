import React, { useState } from 'react';
import type { Evidence, ExtractedEvidence } from '../../domain/canonicalSchema';

interface EvidenceInspectorProps {
  evidenceList: Evidence[];
  extractedEvidence: Record<string, ExtractedEvidence>;
}

export default function EvidenceInspector({ evidenceList, extractedEvidence }: EvidenceInspectorProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!evidenceList || evidenceList.length === 0) {
    return (
      <div className="fabric-panel flex flex-col border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] p-4">
        <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-4 uppercase">EVIDENCE FABRIC</h3>
        <p className="text-xs text-[var(--eureka-text-label)]">No evidence ingested.</p>
      </div>
    );
  }

  return (
    <div className="fabric-panel flex flex-col border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] p-4 overflow-y-auto">
      <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-4 uppercase flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[var(--eureka-signal-semantic)] animate-pulse"></span>
        EVIDENCE FABRIC
      </h3>
      <div className="space-y-4">
        {evidenceList.map((ev) => {
          const isExpanded = expandedId === ev.evidence_id;
          const extracted = extractedEvidence[ev.evidence_id];
          
          let statusColor = "text-[var(--eureka-text-label)]";
          if (ev.extraction_status === "EXTRACTED") statusColor = "text-[var(--eureka-signal-action)]";
          if (ev.extraction_status === "FAILED" || ev.extraction_status === "GAP") statusColor = "text-[var(--eureka-signal-blocked)]";
          if (ev.extraction_status === "PARTIAL") statusColor = "text-yellow-500";
          if (ev.extraction_status === "PARSING") statusColor = "text-blue-400";
          
          return (
            <div key={ev.evidence_id} className="border border-[var(--eureka-spatial-hairline)] bg-[#111116] p-3 rounded">
              <div 
                className="flex justify-between items-center cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : ev.evidence_id)}
              >
                <div className="flex-1 overflow-hidden">
                  <div className="text-sm font-bold truncate text-[var(--eureka-text-display)]" title={ev.filename}>
                    {ev.filename}
                  </div>
                  <div className="text-[10px] text-[var(--eureka-text-label)] mt-1 flex gap-3">
                    <span>{ev.media_type}</span>
                    <span>{(ev.size / 1024).toFixed(1)} KB</span>
                    <span className="font-mono text-[8px] truncate max-w-[100px]" title={ev.sha256}>
                      SHA256: {ev.sha256?.substring(0,8)}...
                    </span>
                  </div>
                </div>
                
                <div className="flex flex-col items-end justify-center ml-4 gap-1">
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border border-current ${statusColor}`}>
                    {ev.extraction_status}
                  </span>
                  <span className="text-[10px] text-[var(--eureka-text-label)]">
                    {isExpanded ? '▲' : '▼'}
                  </span>
                </div>
              </div>
              
              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-[var(--eureka-spatial-hairline)] space-y-4">
                  {/* Metadata */}
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-[10px] text-[var(--eureka-text-label)] uppercase block">Parser</span>
                      <span className="font-mono">{ev.parser_id || 'N/A'} {ev.parser_version ? `v${ev.parser_version}` : ''}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--eureka-text-label)] uppercase block">Ingestion</span>
                      <span className="font-mono">{ev.ingestion_status}</span>
                    </div>
                  </div>
                  
                  {/* Error / Warnings */}
                  {(ev.extraction_error || ev.extraction_reason_code) && (
                    <div className="bg-red-900/20 border border-red-900/50 p-2 text-xs text-red-400">
                      <strong>{ev.extraction_reason_code}</strong>: {ev.extraction_error}
                    </div>
                  )}
                  
                  {extracted?.warnings && extracted.warnings.length > 0 && (
                    <div className="bg-yellow-900/20 border border-yellow-900/50 p-2 text-xs text-yellow-400">
                      <strong className="block mb-1">Warnings:</strong>
                      <ul className="list-disc pl-4 space-y-1">
                        {extracted.warnings.map((w, i) => <li key={i}>{w}</li>)}
                      </ul>
                    </div>
                  )}
                  
                  {/* Extracted Content View */}
                  {extracted && (
                    <div className="space-y-2">
                      <div className="text-[10px] text-[var(--eureka-text-label)] uppercase tracking-widest border-b border-[var(--eureka-spatial-hairline)] pb-1 mb-2">
                        Normalized Evidence View ({extracted.extraction_method})
                      </div>
                      
                      <div className="max-h-[300px] overflow-y-auto bg-black/50 p-3 font-mono text-[10px] text-[var(--eureka-text-section)] space-y-3">
                        {extracted.structured_data && (
                          <div className="text-blue-300">
                            <strong>Structured Data:</strong>
                            <pre className="mt-1 opacity-80">{JSON.stringify(extracted.structured_data, null, 2)}</pre>
                          </div>
                        )}
                        
                        {extracted.sheets && extracted.sheets.length > 0 && (
                          <div className="text-green-300">
                            <strong>Sheets ({extracted.sheets.length}):</strong>
                            <ul className="list-disc pl-4 mt-1 opacity-80">
                              {extracted.sheets.map((s, i) => <li key={i}>{s}</li>)}
                            </ul>
                          </div>
                        )}
                        
                        {extracted.text_blocks && extracted.text_blocks.length > 0 && (
                          <div className="text-gray-300 space-y-2">
                            <strong>Text Blocks ({extracted.text_blocks.length}):</strong>
                            {extracted.text_blocks.map((b, i) => (
                              <div key={i} className="border-l border-gray-700 pl-2 opacity-80 whitespace-pre-wrap">
                                {typeof b === 'string' ? (b.length > 300 ? b.substring(0, 300) + '...' : b) : JSON.stringify(b)}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      {/* Provenance */}
                      <div className="mt-3">
                        <div className="text-[10px] text-[var(--eureka-text-label)] uppercase block mb-1">Source Locations</div>
                        <div className="flex flex-wrap gap-1">
                          {extracted.source_locations?.slice(0, 5).map((loc, i) => (
                            <span key={i} className="bg-[var(--eureka-spatial-hairline)] px-1.5 py-0.5 rounded text-[8px] font-mono">
                              {loc}
                            </span>
                          ))}
                          {(extracted.source_locations?.length || 0) > 5 && (
                            <span className="text-[8px] text-[var(--eureka-text-label)] self-center">
                              +{extracted.source_locations.length - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Base Provenance */}
                  {ev.provenance && ev.provenance.length > 0 && (
                    <div className="pt-2 border-t border-[var(--eureka-spatial-hairline)] text-[10px] text-[var(--eureka-text-label)] font-mono">
                      <div className="mb-1 uppercase tracking-widest text-[8px]">Origin Trail</div>
                      {ev.provenance.map((p, i) => (
                        <div key={i} className="truncate">→ {p}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
