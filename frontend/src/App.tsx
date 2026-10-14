import React, { useState, useEffect } from 'react';
import { 
  Upload, Shield, FileText, History, AlertTriangle, CheckCircle2, 
  HelpCircle, Cpu, ArrowRight, RefreshCw, Download, Layers, Sparkles
} from 'lucide-react';
import type { ScanResult, ScanItem, VerdictLabel, RiskLevel } from './types';

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
      const res = await fetch('http://localhost:8000/api/scans?limit=20');
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
      const res = await fetch('http://localhost:8000/api/scans', {
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
      const res = await fetch(`http://localhost:8000/api/scans/${scanId}`);
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
        return <span className="px-3 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5"><AlertTriangle size={14}/> LIKELY AI-GENERATED</span>;
      case 'LIKELY_REAL':
        return <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5"><CheckCircle2 size={14}/> LIKELY AUTHENTIC</span>;
      case 'INCONCLUSIVE':
        return <span className="px-3 py-1 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5"><HelpCircle size={14}/> INCONCLUSIVE</span>;
      default:
        return <span className="px-3 py-1 bg-slate-700/50 text-slate-300 border border-slate-600 rounded-full text-xs font-semibold">ANALYSIS FAILED</span>;
    }
  };

  const getRiskBadge = (risk: RiskLevel) => {
    const colors: Record<RiskLevel, string> = {
      low: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/50',
      moderate: 'text-amber-400 bg-amber-950/40 border-amber-800/50',
      high: 'text-red-400 bg-red-950/40 border-red-800/50',
      unknown: 'text-slate-400 bg-slate-900 border-slate-700',
    };
    return <span className={`px-2.5 py-1 rounded text-xs uppercase font-mono border ${colors[risk]}`}>Risk: {risk}</span>;
  };

  const formatArtifactUrl = (artifactPath?: string | null) => {
    if (!artifactPath) return null;
    const parts = artifactPath.split('artifacts/');
    if (parts.length > 1) {
      return `http://localhost:8000/api/artifacts/${parts[1]}`;
    }
    return `http://localhost:8000/api/artifacts/${artifactPath}`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 border border-blue-500/30 rounded-lg text-blue-400">
            <Shield size={24} />
          </div>
          <div>
            <h1 className="font-bold tracking-wider text-lg text-slate-100">PHANTOM PHOENIX</h1>
            <p className="text-xs text-slate-400">Digital Media Authenticity & Forensic Intelligence</p>
          </div>
        </div>
        <nav className="flex items-center gap-2">
          <button 
            onClick={() => { setActiveTab('upload'); setCurrentScan(null); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${activeTab === 'upload' && !currentScan ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            New Scan
          </button>
          <button 
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${activeTab === 'history' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            <History size={16} /> Scan History
          </button>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col">
        {activeTab === 'history' && !currentScan && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Scan Archive</h2>
                <p className="text-sm text-slate-400">Previously analyzed images persisted in PostgreSQL</p>
              </div>
              <button 
                onClick={loadHistory} 
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs flex items-center gap-1.5 transition"
              >
                <RefreshCw size={12} className={historyLoading ? "animate-spin" : ""} /> Refresh
              </button>
            </div>

            {historyLoading && history.length === 0 ? (
              <div className="py-20 text-center text-slate-500">Loading scan history...</div>
            ) : history.length === 0 ? (
              <div className="py-20 text-center border border-dashed border-slate-800 rounded-xl">
                <History size={40} className="mx-auto text-slate-600 mb-3" />
                <p className="text-slate-400">No scans recorded yet.</p>
                <button 
                  onClick={() => setActiveTab('upload')} 
                  className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition"
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
                    className="p-4 bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-xl flex items-center justify-between cursor-pointer transition group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-slate-800 rounded-lg text-slate-400 group-hover:text-blue-400 transition">
                        <FileText size={20} />
                      </div>
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-slate-200">{item.input.filename}</span>
                          {getVerdictBadge(item.verdict.label)}
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-xs text-slate-400 font-mono">
                          <span>SHA: {item.input.sha256.substring(0, 12)}...</span>
                          <span>{item.input.width}×{item.input.height}px</span>
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {getRiskBadge(item.verdict.risk)}
                      <ArrowRight size={16} className="text-slate-600 group-hover:text-slate-300 transition" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {(!currentScan && activeTab === 'upload') && (
          <div className="max-w-3xl mx-auto w-full my-auto py-12 space-y-8">
            <div className="text-center space-y-3">
              <h2 className="text-3xl font-extrabold tracking-tight text-slate-100">Upload Evidence for Forensic Analysis</h2>
              <p className="text-slate-400 text-sm max-w-xl mx-auto">
                Upload JPEG, PNG, or WEBP images. The platform runs Vision Transformer AI detection, Metadata inspection, Error Level Analysis (ELA), Noise residuals, and 2D FFT Frequency spectra.
              </p>
            </div>

            <div 
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className="border-2 border-dashed border-slate-700 hover:border-blue-500/50 bg-slate-900/40 rounded-2xl p-10 text-center transition flex flex-col items-center justify-center relative cursor-pointer"
            >
              <input 
                type="file" 
                accept="image/jpeg,image/png,image/webp" 
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <div className="p-4 bg-blue-600/10 border border-blue-500/20 rounded-full text-blue-400 mb-4">
                <Upload size={32} />
              </div>
              <h3 className="text-lg font-semibold text-slate-200 mb-1">
                {file ? file.name : "Drag & drop image here, or click to browse"}
              </h3>
              <p className="text-xs text-slate-500">Supports JPEG, PNG, WEBP up to 15 MiB (Max 8192px per side)</p>

              {file && (
                <div className="mt-6 flex items-center gap-3 bg-slate-800/80 px-4 py-2 rounded-lg border border-slate-700">
                  <span className="text-xs text-slate-300 font-mono">{(file.size / 1024).toFixed(1)} KB</span>
                  <button 
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    className="text-xs text-red-400 hover:text-red-300 ml-2"
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>

            {error && (
              <div className="p-4 bg-red-950/40 border border-red-800/50 rounded-xl text-red-300 text-sm flex items-center gap-3">
                <AlertTriangle size={18} className="shrink-0 text-red-400" />
                <span>{error}</span>
              </div>
            )}

            <button 
              onClick={handleUpload}
              disabled={!file || loading}
              className="w-full py-3.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold rounded-xl shadow-lg transition flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw size={18} className="animate-spin" />
                  Analyzing Evidence...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Run Forensic Scan
                </>
              )}
            </button>
          </div>
        )}

        {currentScan && (
          <div className="space-y-8 pb-12">
            {/* Top Bar for Results */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-xs font-mono text-slate-400">SCAN ID: {currentScan.scan_id}</span>
                  {getVerdictBadge(currentScan.verdict.label)}
                  {getRiskBadge(currentScan.verdict.risk)}
                </div>
                <h2 className="text-xl font-bold text-slate-100">{currentScan.input.filename}</h2>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  SHA-256: {currentScan.input.sha256} | {currentScan.input.width}×{currentScan.input.height}px | {(currentScan.input.byte_size / 1024).toFixed(1)} KB ({currentScan.input.media_type})
                </p>
              </div>
              <div className="flex items-center gap-3">
                <a 
                  href={`http://localhost:8000/api/scans/${currentScan.scan_id}/report.pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-medium transition flex items-center gap-2 border border-slate-700"
                >
                  <Download size={16} /> Download PDF Report
                </a>
                <button 
                  onClick={() => setCurrentScan(null)}
                  className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition"
                >
                  New Scan
                </button>
              </div>
            </div>

            {/* AI Detector & Verdict Rationale */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-slate-900/60 border border-slate-800 p-6 rounded-2xl space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-200 flex items-center gap-2">
                    <Cpu size={18} className="text-blue-400" /> AI Detection Model
                  </h3>
                  <span className="text-xs font-mono text-slate-400">ViT-Small (Community Forensics)</span>
                </div>
                {currentScan.models[0] && (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-xl border border-slate-700/50">
                      <span className="text-sm text-slate-300">Fake Probability</span>
                      <span className="font-mono font-bold text-lg text-slate-100">
                        {currentScan.models[0].fake_probability !== null 
                          ? `${(currentScan.models[0].fake_probability * 100).toFixed(2)}%` 
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono text-slate-400">
                      <div className="p-2.5 bg-slate-800/30 rounded-lg border border-slate-800">
                        Raw Logit: {currentScan.models[0].raw_logit?.toFixed(4) ?? 'N/A'}
                      </div>
                      <div className="p-2.5 bg-slate-800/30 rounded-lg border border-slate-800">
                        Device: {currentScan.models[0].device ?? 'N/A'} ({currentScan.models[0].duration_seconds}s)
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-slate-900/60 border border-slate-800 p-6 rounded-2xl space-y-4">
                <h3 className="font-semibold text-slate-200 flex items-center gap-2">
                  <FileText size={18} className="text-amber-400" /> Verdict Rationale
                </h3>
                <ul className="space-y-2 text-sm text-slate-300">
                  {currentScan.verdict.rationale.map((rat, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-blue-400 font-bold">•</span>
                      <span>{rat}</span>
                    </li>
                  ))}
                </ul>
                <div className="pt-2 border-t border-slate-800 text-xs text-slate-500">
                  <span className="font-semibold text-slate-400">Explicitly Not Claimed:</span> {currentScan.verdict.not_claimed.join('; ')}
                </div>
              </div>
            </div>

            {/* Evidence Items / Forensic Indicators */}
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                <Layers size={20} className="text-purple-400" /> Normalized Evidence & Forensic Analyzers
              </h3>

              <div className="grid md:grid-cols-2 gap-4">
                {(currentScan.evidence_items || []).map((ev) => (
                  <div key={ev.id} className="bg-slate-900/60 border border-slate-800 p-5 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold uppercase text-xs px-2 py-0.5 bg-slate-800 rounded text-slate-300 font-mono">{ev.id}</span>
                        <span className="text-xs px-2 py-0.5 bg-blue-950/60 text-blue-400 border border-blue-800/40 rounded font-mono">{ev.evidence_category}</span>
                      </div>
                      <span className="text-xs font-mono text-slate-400 uppercase">Method: {ev.method}</span>
                    </div>

                    <p className="text-sm text-slate-300">{ev.interpretation || "No interpretation provided."}</p>

                    {ev.result && Object.keys(ev.result).length > 0 && (
                      <div className="bg-slate-950/60 p-3 rounded-lg font-mono text-xs text-slate-400 overflow-x-auto border border-slate-800">
                        <pre>{JSON.stringify(ev.result, null, 2)}</pre>
                      </div>
                    )}

                    {ev.artifact && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <p className="text-xs text-slate-400 mb-2 font-semibold">Generated Artifact ({ev.id}):</p>
                        <div className="rounded-lg overflow-hidden border border-slate-700 bg-slate-955 max-h-60 flex items-center justify-center">
                          <img 
                            src={formatArtifactUrl(ev.artifact) || ''} 
                            alt={`${ev.id} artifact`} 
                            className="object-contain max-h-60 w-full"
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
      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500 font-mono">
        PHANTOM PHOENIX FORENSIC INTELLIGENCE ENGINE • SCREENING AID ONLY • NOT LEGAL PROOF
      </footer>
    </div>
  );
}

export default App;
