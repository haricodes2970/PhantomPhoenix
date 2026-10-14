import React, { useState, useEffect } from 'react';
import { 
  Upload, Shield, FileText, History, AlertTriangle, CheckCircle2, 
  HelpCircle, Cpu, ArrowRight, RefreshCw, Download, Layers, Sparkles
} from 'lucide-react';
import type { ScanResult, ScanItem, VerdictLabel, RiskLevel } from './types';

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState<'upload' | 'history'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentScan, setCurrentScan] = useState<ScanResult | null>(null);
  
  const [history, setHistory] = useState<ScanItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab]);

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/scans?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.scans || []);
      }
    } catch (err) {
      console.error('Failed to load history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/scans`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error?.message || 'Analysis failed');
      }

      const data = await res.json();
      setCurrentScan(data.result);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred during analysis.');
    } finally {
      setLoading(false);
    }
  };

  const fetchScanById = async (scanId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/scans/${scanId}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentScan(data);
      } else {
        throw new Error('Scan not found');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getVerdictBadge = (label: VerdictLabel) => {
    switch (label) {
      case 'LIKELY_AI':
        return <span className="px-2.5 py-1 bg-white text-black border border-white rounded text-xs font-mono font-bold flex items-center gap-1.5"><AlertTriangle size={13}/> LIKELY AI-GENERATED</span>;
      case 'LIKELY_REAL':
        return <span className="px-2.5 py-1 bg-black text-white border border-white rounded text-xs font-mono font-bold flex items-center gap-1.5"><CheckCircle2 size={13}/> LIKELY AUTHENTIC</span>;
      case 'INCONCLUSIVE':
        return <span className="px-2.5 py-1 bg-neutral-800 text-neutral-200 border border-neutral-600 rounded text-xs font-mono font-bold flex items-center gap-1.5"><HelpCircle size={13}/> INCONCLUSIVE</span>;
      default:
        return <span className="px-2.5 py-1 bg-neutral-900 text-neutral-400 border border-neutral-700 rounded text-xs font-mono font-bold">ANALYSIS FAILED</span>;
    }
  };

  const getRiskBadge = (risk: RiskLevel) => {
    return <span className="px-2 py-0.5 rounded text-xs uppercase font-mono border border-neutral-700 bg-neutral-900 text-neutral-300">Risk: {risk}</span>;
  };

  const formatArtifactUrl = (artifactPath?: string | null) => {
    if (!artifactPath) return null;
    const parts = artifactPath.split('artifacts/');
    if (parts.length > 1) {
      return `${API_BASE}/api/artifacts/${parts[1]}`;
    }
    return `${API_BASE}/api/artifacts/${artifactPath}`;
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col font-sans selection:bg-white selection:text-black">
      {/* Top Navbar */}
      <header className="border-b border-neutral-800 bg-black sticky top-0 z-50 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 border border-white text-white">
            <Shield size={20} />
          </div>
          <div>
            <h1 className="font-mono font-bold tracking-widest text-sm uppercase text-white">PHANTOM PHOENIX</h1>
            <p className="text-[10px] text-neutral-400 font-mono tracking-wider">DIGITAL MEDIA FORENSICS & AUTHENTICITY</p>
          </div>
        </div>
        <nav className="flex items-center gap-3">
          <button 
            onClick={() => { setActiveTab('upload'); setCurrentScan(null); }}
            className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition ${activeTab === 'upload' && !currentScan ? 'bg-white text-black font-bold' : 'text-neutral-400 hover:text-white hover:bg-neutral-900'}`}
          >
            New Scan
          </button>
          <button 
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition flex items-center gap-2 ${activeTab === 'history' ? 'bg-white text-black font-bold' : 'text-neutral-400 hover:text-white hover:bg-neutral-900'}`}
          >
            <History size={14} /> Scan Archive
          </button>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-8 flex flex-col">
        {activeTab === 'history' && !currentScan && (
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-neutral-800 pb-4">
              <div>
                <h2 className="text-xl font-mono uppercase tracking-wider text-white">Scan Archive</h2>
                <p className="text-xs text-neutral-400 font-mono mt-1">Persisted forensic inspection records</p>
              </div>
              <button 
                onClick={loadHistory} 
                className="px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-700 rounded text-xs font-mono flex items-center gap-1.5 transition"
              >
                <RefreshCw size={12} className={historyLoading ? "animate-spin" : ""} /> Refresh
              </button>
            </div>

            {historyLoading && history.length === 0 ? (
              <div className="py-20 text-center text-neutral-500 font-mono text-xs">Loading records...</div>
            ) : history.length === 0 ? (
              <div className="py-20 text-center border border-dashed border-neutral-800 rounded">
                <History size={32} className="mx-auto text-neutral-600 mb-3" />
                <p className="text-neutral-400 font-mono text-xs">No scan records found.</p>
                <button 
                  onClick={() => setActiveTab('upload')} 
                  className="mt-4 px-4 py-2 bg-white text-black font-mono text-xs uppercase font-bold rounded transition"
                >
                  Upload Image
                </button>
              </div>
            ) : (
              <div className="grid gap-3">
                {history.map((item) => (
                  <div 
                    key={item.scan_id}
                    onClick={() => fetchScanById(item.scan_id)}
                    className="p-4 bg-neutral-950 border border-neutral-800 hover:border-neutral-600 rounded flex items-center justify-between cursor-pointer transition group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-2.5 bg-neutral-900 border border-neutral-800 rounded text-neutral-400 group-hover:text-white transition">
                        <FileText size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm text-neutral-200">{item.input.filename}</span>
                          {getVerdictBadge(item.verdict.label)}
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-[11px] text-neutral-400 font-mono">
                          <span>SHA: {item.input.sha256.substring(0, 16)}...</span>
                          <span>{item.input.width}×{item.input.height}px</span>
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {getRiskBadge(item.verdict.risk)}
                      <ArrowRight size={16} className="text-neutral-600 group-hover:text-white transition" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {(!currentScan && activeTab === 'upload') && (
          <div className="max-w-2xl mx-auto w-full my-auto py-16 space-y-8">
            <div className="text-center space-y-3">
              <h2 className="text-2xl font-mono uppercase tracking-widest text-white">Forensic Evidence Ingestion</h2>
              <p className="text-neutral-400 text-xs font-mono leading-relaxed max-w-lg mx-auto">
                Upload image evidence (JPEG, PNG, WEBP). Pipeline executes Vision Transformer AI detection, EXIF/XMP inspection, Error Level Analysis (ELA), Noise residuals, and 2D FFT Frequency spectra.
              </p>
            </div>

            <div 
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className="border border-neutral-700 hover:border-white bg-neutral-950 rounded p-12 text-center transition flex flex-col items-center justify-center relative cursor-pointer"
            >
              <input 
                type="file" 
                accept="image/jpeg,image/png,image/webp" 
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <div className="p-3 border border-neutral-700 rounded text-neutral-300 mb-4 bg-neutral-900">
                <Upload size={24} />
              </div>
              <h3 className="text-sm font-mono text-neutral-200 mb-1">
                {file ? file.name : "Drag & drop file here, or click to select"}
              </h3>
              <p className="text-[11px] text-neutral-500 font-mono">Max size 15 MiB • Max dimensions 8192px per side</p>

              {file && (
                <div className="mt-6 flex items-center gap-3 bg-neutral-900 px-3 py-1.5 rounded border border-neutral-800">
                  <span className="text-[11px] text-neutral-300 font-mono">{(file.size / 1024).toFixed(1)} KB</span>
                  <button 
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    className="text-[11px] text-neutral-400 hover:text-white ml-2 underline font-mono"
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>

            {error && (
              <div className="p-3 bg-neutral-900 border border-neutral-700 rounded text-neutral-200 text-xs font-mono flex items-center gap-3">
                <AlertTriangle size={16} className="shrink-0 text-white" />
                <span>{error}</span>
              </div>
            )}

            <button 
              onClick={handleUpload}
              disabled={!file || loading}
              className="w-full py-3 bg-white hover:bg-neutral-200 disabled:bg-neutral-900 disabled:text-neutral-600 text-black font-mono text-xs uppercase font-bold tracking-widest rounded transition flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  Executing Forensic Pipeline...
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  Initiate Inspection Scan
                </>
              )}
            </button>
          </div>
        )}

        {currentScan && (
          <div className="space-y-6 pb-12">
            {/* Top Bar for Results */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-neutral-950 border border-neutral-800 p-6 rounded">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-[11px] font-mono text-neutral-400">SCAN ID: {currentScan.scan_id}</span>
                  {getVerdictBadge(currentScan.verdict.label)}
                  {getRiskBadge(currentScan.verdict.risk)}
                </div>
                <h2 className="text-lg font-mono text-white">{currentScan.input.filename}</h2>
                <p className="text-[11px] text-neutral-400 mt-1 font-mono">
                  SHA-256: {currentScan.input.sha256} | {currentScan.input.width}×{currentScan.input.height}px | {(currentScan.input.byte_size / 1024).toFixed(1)} KB ({currentScan.input.media_type})
                </p>
              </div>
              <div className="flex items-center gap-3">
                <a 
                  href={`${API_BASE}/api/scans/${currentScan.scan_id}/report.pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 text-white rounded text-xs font-mono uppercase tracking-wider transition flex items-center gap-2 border border-neutral-700"
                >
                  <Download size={14} /> Download PDF Report
                </a>
                <button 
                  onClick={() => setCurrentScan(null)}
                  className="px-4 py-2 bg-white text-black hover:bg-neutral-200 rounded text-xs font-mono uppercase font-bold tracking-wider transition"
                >
                  New Scan
                </button>
              </div>
            </div>

            {/* AI Detector & Verdict Rationale */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-neutral-950 border border-neutral-800 p-6 rounded space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <h3 className="font-mono text-xs uppercase tracking-wider text-white flex items-center gap-2">
                    <Cpu size={16} className="text-neutral-400" /> AI Detection Model
                  </h3>
                  <span className="text-[11px] font-mono text-neutral-400">ViT-Small</span>
                </div>
                {currentScan.models[0] && (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-neutral-900 rounded border border-neutral-800">
                      <span className="text-xs font-mono text-neutral-300">Fake Probability</span>
                      <span className="font-mono font-bold text-base text-white">
                        {currentScan.models[0].fake_probability !== null 
                          ? `${(currentScan.models[0].fake_probability * 100).toFixed(2)}%` 
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-neutral-400">
                      <div className="p-2 bg-neutral-900 rounded border border-neutral-800">
                        Logit: {currentScan.models[0].raw_logit?.toFixed(4) ?? 'N/A'}
                      </div>
                      <div className="p-2 bg-neutral-900 rounded border border-neutral-800">
                        Device: {currentScan.models[0].device ?? 'N/A'} ({currentScan.models[0].duration_seconds}s)
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-neutral-950 border border-neutral-800 p-6 rounded space-y-4">
                <h3 className="font-mono text-xs uppercase tracking-wider text-white flex items-center gap-2 border-b border-neutral-800 pb-3">
                  <FileText size={16} className="text-neutral-400" /> Verdict Rationale
                </h3>
                <ul className="space-y-2 text-xs font-mono text-neutral-300">
                  {currentScan.verdict.rationale.map((rat, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-white font-bold">—</span>
                      <span>{rat}</span>
                    </li>
                  ))}
                </ul>
                <div className="pt-2 border-t border-neutral-800 text-[10px] text-neutral-500 font-mono">
                  <span className="font-semibold text-neutral-400">Explicitly Not Claimed:</span> {currentScan.verdict.not_claimed.join('; ')}
                </div>
              </div>
            </div>

            {/* Evidence Items / Forensic Indicators */}
            <div className="space-y-4">
              <h3 className="text-sm font-mono uppercase tracking-wider text-white flex items-center gap-2">
                <Layers size={16} className="text-neutral-400" /> Normalized Evidence & Forensic Analyzers
              </h3>

              <div className="grid md:grid-cols-2 gap-4">
                {(currentScan.evidence_items || []).map((ev) => (
                  <div key={ev.id} className="bg-neutral-950 border border-neutral-800 p-5 rounded space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs uppercase px-2 py-0.5 bg-neutral-900 border border-neutral-700 rounded text-white font-bold">{ev.id}</span>
                        <span className="text-[10px] px-2 py-0.5 bg-neutral-900 text-neutral-300 border border-neutral-800 rounded font-mono">{ev.evidence_category}</span>
                      </div>
                      <span className="text-[10px] font-mono text-neutral-500 uppercase">Method: {ev.method}</span>
                    </div>

                    <p className="text-xs font-mono text-neutral-300 leading-relaxed">{ev.interpretation || "No interpretation provided."}</p>

                    {ev.result && Object.keys(ev.result).length > 0 && (
                      <div className="bg-black p-3 rounded font-mono text-[10px] text-neutral-400 overflow-x-auto border border-neutral-800">
                        <pre>{JSON.stringify(ev.result, null, 2)}</pre>
                      </div>
                    )}

                    {ev.artifact && (
                      <div className="mt-3 pt-3 border-t border-neutral-800">
                        <p className="text-[11px] text-neutral-400 mb-2 font-mono uppercase">Generated Artifact ({ev.id}):</p>
                        <div className="rounded overflow-hidden border border-neutral-800 bg-black max-h-56 flex items-center justify-center">
                          <img 
                            src={formatArtifactUrl(ev.artifact) || ''} 
                            alt={`${ev.id} artifact`} 
                            className="object-contain max-h-56 w-full"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-800 py-6 text-center text-[10px] text-neutral-500 font-mono tracking-widest uppercase">
        PHANTOM PHOENIX FORENSIC INTELLIGENCE ENGINE • SCREENING AID ONLY • NOT LEGAL PROOF
      </footer>
    </div>
  );
}

export default App;
