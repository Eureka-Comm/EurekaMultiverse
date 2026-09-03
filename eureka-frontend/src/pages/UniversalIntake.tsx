import React, { useState, useRef, useEffect } from 'react';
import { useWorkStore } from '../store/workStore';

export default function UniversalIntake() {
  const startWork = useWorkStore((state) => state.startWork);
  const [intent, setIntent] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  const [evidenceIds, setEvidenceIds] = useState<string[]>([]);
  const [uploadStatus, setUploadStatus] = useState<'IDLE' | 'UPLOADING' | 'EVIDENCE INGESTED' | 'EUREKA EVIDENCE ERROR'>('IDLE');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCustomSubmit = async () => {
    if (intent.trim() && !isProcessing) {
      setIsProcessing(true);
      await startWork(intent, 'UNKNOWN', evidenceIds);
      setIsProcessing(false);
    }
  };
useEffect(() => {
  console.log('UniversalIntake debug - intent:', intent);
  console.log('Button disabled state:', !intent.trim() || isProcessing);
}, [intent, isProcessing]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setUploadStatus('UPLOADING');
      
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const apiUrl = import.meta.env.VITE_EUREKA_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/evidence`, {
          method: 'POST',
          body: formData
        });
        
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`HTTP ${res.status}: ${errText}`);
        }
        
        const data = await res.json();
        setEvidenceIds(prev => [...prev, data.evidence_id]);
        setUploadStatus('EVIDENCE INGESTED');
      } catch (err: any) {
        console.error(err);
        setUploadStatus(`EUREKA EVIDENCE ERROR: ${err.message}` as any);
      }
    }
  };

  return (
    <div className="min-h-screen bg-white text-[var(--eureka-text-display)] p-12 flex flex-col items-center justify-center">
      <div className="w-full max-w-4xl space-y-16">
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-light tracking-tight">EUREKA MULTIVERSE</h1>
          <h2 className="text-2xl text-[var(--eureka-text-label)]">WHAT ARE YOU TRYING TO ACCOMPLISH?</h2>
        </div>

        <div className="space-y-6">
          <div className="fabric-panel p-8 space-y-6 rounded-lg bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] shadow-2xl">
            <label className="block text-sm text-[var(--eureka-text-label)]">
              Describe the problem, objective, question or work.
            </label>
            <textarea
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleCustomSubmit();
                }
              }}
              disabled={isProcessing}
              className="w-full h-40 bg-transparent border border-[var(--eureka-spatial-hairline)] rounded p-4 text-lg text-[var(--eureka-text-display)] focus:outline-none focus:border-[var(--eureka-signal-cognitive)] transition-colors resize-none placeholder-[var(--eureka-text-label)] opacity-70"
              placeholder='e.g., "Tengo 50,000 pesos y quiero decidir..."'
            />
            
            <div className="flex flex-col gap-2">
              {evidenceIds.length > 0 && (
                <div className="text-xs text-[var(--eureka-text-label)]">
                  {evidenceIds.length} evidence file(s) ready
                </div>
              )}
              {uploadStatus !== 'IDLE' && (
                <div className={`text-xs ${uploadStatus === 'EUREKA EVIDENCE ERROR' ? 'text-red-500' : uploadStatus === 'UPLOADING' ? 'text-yellow-500 animate-pulse' : 'text-green-500'}`}>
                  {uploadStatus}
                </div>
              )}
            </div>

            <div className="flex justify-between items-center">
              <div>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  className="hidden" 
                />
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadStatus === 'UPLOADING'}
                  className="text-sm text-[var(--eureka-text-label)] hover:text-white flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  <span>📎 Attach evidence</span>
                </button>
              </div>
              <button
                onClick={handleCustomSubmit}
                disabled={!intent.trim() || isProcessing}
                className={`px-8 py-3 rounded text-sm font-bold tracking-wider transition-colors ${
                  intent.trim() && !isProcessing
                    ? 'bg-[var(--eureka-signal-cognitive)] text-white hover:opacity-90' 
                    : 'bg-[var(--eureka-surface-elevated)] text-[var(--eureka-text-label)] cursor-not-allowed'
                }`}
              >
                {isProcessing ? 'UNDERSTANDING PROBLEM...' : 'Ask'}
              </button>
            </div>
          </div>
          
          <div className="text-center">
            <p className="text-xs text-[var(--eureka-text-label)] tracking-widest uppercase">EUREKA WILL DETERMINE THE WORK</p>
          </div>
        </div>
      </div>
    </div>
  );
}
