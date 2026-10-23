import React, { useState, useEffect } from 'react';
import {
  Upload, FileText, History, AlertTriangle, CheckCircle2,
  HelpCircle, Cpu, ArrowRight, RefreshCw, Download, Layers, Sparkles,
  Terminal, Search, Database, Lock, Activity, BarChart3, CheckCircle, XCircle, Zap,
  ArrowUpDown
} from 'lucide-react';
import type { ScanResult, ScanItem, VerdictLabel, RiskLevel, HealthResponse } from './types';

// Same-origin by default in production builds (the frontend nginx proxies
// /api to the backend); localhost:8000 fallback preserves `npm run dev`.
// Absolute URLs must come from build-time VITE_API_BASE only — never from
// runtime user input.
const API_BASE: string = (import.meta as any).env?.VITE_API_BASE
  || (import.meta.env && import.meta.env.PROD ? '' : 'http://localhost:8000');

// ---------------------------------------------------------------------------
// Authentication state types (Milestone 12)
// ---------------------------------------------------------------------------
interface AuthIdentity {
  user_id: string;
  username: string;
  role: string;
}
type AuthResolved = 'unknown' | 'guest' | 'authed';

/** Sentinel thrown when the backend reports a missing/expired session. */
class SessionExpiredError extends Error {
  constructor() {
    super('Your session has expired. Please sign in again.');
    this.name = 'SessionExpiredError';
  }
}

/**
 * Authenticated API client.
 * - Sends the HttpOnly session cookie on every call (credentials include).
 * - Never touches localStorage/sessionStorage (no secrets client-side).
 * - On 401: clears auth state and routes to the login view.
 * - On 403/429: raises a user-readable error (Retry-After honored for 429).
 */
async function authFetch(path: string, options: RequestInit, handlers: {
  onSessionExpired: () => void;
}): Promise<Response> {
  const res = await fetch(path, {
    credentials: 'include',
    ...options,
  });
  if (res.status === 401) {
    handlers.onSessionExpired();
    throw new SessionExpiredError();
  }
  if (res.status === 429) {
    const retryAfter = res.headers.get('Retry-After');
    const waitNote = retryAfter ? ` Try again in ${retryAfter}s.` : ' Please slow down and try again later.';
    throw new Error(`Rate limit exceeded.${waitNote}`);
  }
  return res;
}

export type PhoenixState = 'idle' | 'investigating' | 'processing' | 'reassuring' | 'warning' | 'inconclusive' | 'error';

interface PhoenixMascotProps {
  state: PhoenixState;
  size?: 'sm' | 'md' | 'lg';
  ariaLabel?: string;
}

/**
 * Original pixel-art phoenix. Red/orange/gold plumage, intentional blue/cyan
 * magic accents (third-eye diamond + aura ring when investigating), flame
 * tail. Per-state palette drives body hue; magic accents stay blue/cyan on
 * "investigating" and cool to state colors elsewhere.
 */
const PHOENIX_PALETTE: Record<PhoenixState, { body: string; wing: string; flame: string; accent: string; magic: string; eye: string; anim: string }> = {
  idle:          { body: '#f59e0b', wing: '#ef4444', flame: '#fbbf24', accent: '#ef4444', magic: '#38bdf8', eye: '#fff7ed', anim: 'animate-phoenix-pulse' },
  investigating: { body: '#38bdf8', wing: '#fb923c', flame: '#fde047', accent: '#22d3ee', magic: '#67e8f9', eye: '#ecfeff', anim: 'animate-phoenix-scan' },
  processing:    { body: '#a855f7', wing: '#f97316', flame: '#fcd34d', accent: '#22d3ee', magic: '#c4b5fd', eye: '#faf5ff', anim: 'animate-phoenix-pulse' },
  reassuring:    { body: '#10b981', wing: '#f59e0b', flame: '#fbbf24', accent: '#ef4444', magic: '#38bdf8', eye: '#ecfdf5', anim: 'animate-phoenix-pulse' },
  warning:       { body: '#ef4444', wing: '#b91c1c', flame: '#f97316', accent: '#fbbf24', magic: '#fb7185', eye: '#fee2e2', anim: 'animate-phoenix-pulse' },
  inconclusive:  { body: '#f59e0b', wing: '#d97706', flame: '#fcd34d', accent: '#ef4444', magic: '#38bdf8', eye: '#fffbeb', anim: 'animate-phoenix-pulse' },
  error:         { body: '#dc2626', wing: '#991b1b', flame: '#78350f', accent: '#ef4444', magic: '#fca5a5', eye: '#fee2e2', anim: 'animate-phoenix-pulse' },
};

// Pixel-grid (16x14). Each tuple = [x, y, w, h, paletteKey].
// Drawn as flat rects for crisp pixel-art rendering (`pixel-art` class).
const PHOENIX_BODY: Array<[number, number, number, number, 'body' | 'wing' | 'flame' | 'accent' | 'eye' | 'magic']> = [
  // crest / head
  [7, 0, 2, 1, 'accent'],
  [6, 1, 4, 2, 'body'],
  [5, 2, 6, 2, 'wing'],
  // face + eye (magic diamond)
  [6, 4, 4, 1, 'body'],
  [4, 4, 1, 1, 'magic'],
  [11, 4, 1, 1, 'magic'],
  [7, 4, 1, 1, 'eye'],
  [8, 4, 1, 1, 'body'],
  [5, 5, 6, 2, 'body'],
  [6, 5, 1, 1, 'eye'],
  // beak
  [9, 5, 2, 1, 'flame'],
  [9, 6, 1, 1, 'flame'],
  // neck + chest (gold belly)
  [6, 7, 4, 1, 'wing'],
  [7, 7, 2, 2, 'flame'],
  // wings spread (left + right, orange/red plumage)
  [1, 5, 3, 1, 'wing'],
  [0, 6, 2, 2, 'wing'],
  [1, 8, 2, 1, 'wing'],
  [3, 6, 2, 2, 'body'],
  [12, 5, 3, 1, 'wing'],
  [14, 6, 2, 2, 'wing'],
  [13, 8, 2, 1, 'wing'],
  [11, 6, 2, 2, 'body'],
  // body core
  [6, 9, 4, 1, 'wing'],
  [7, 9, 2, 1, 'body'],
  // tail flames (gold → orange ascent)
  [6, 10, 1, 2, 'flame'],
  [9, 10, 1, 2, 'flame'],
  [7, 10, 2, 1, 'wing'],
  [7, 11, 2, 2, 'wing'],
  [5, 10, 1, 1, 'flame'],
  [10, 10, 1, 1, 'flame'],
  [7, 13, 2, 1, 'flame'],
];

export function PhoenixMascot({ state, size = 'md', ariaLabel }: PhoenixMascotProps) {
  const dimensionClass = size === 'sm' ? 'w-10 h-10' : size === 'lg' ? 'w-24 h-24' : 'w-16 h-16';
  const palette = PHOENIX_PALETTE[state];
  const label = ariaLabel || `Phoenix mascot in ${state} state`;
  const showAura = state === 'investigating';

  return (
    <div
      role="img"
      aria-label={label}
      className={`relative inline-flex items-center justify-center p-1.5 rounded bg-black/60 border border-neutral-800 ${dimensionClass} ${palette.anim} pixel-art`}
    >
      {showAura && (
        <span
          aria-hidden="true"
          className="absolute inset-0 rounded opacity-60 pointer-events-none"
          style={{ boxShadow: `0 0 8px 2px ${palette.magic}, inset 0 0 4px 1px ${palette.accent}` }}
        />
      )}
      <svg viewBox="0 0 16 14" className="w-full h-full" shapeRendering="crispEdges" xmlns="http://www.w3.org/2000/svg">
        {PHOENIX_BODY.map(([x, y, w, h, key], i) => (
          <rect key={i} x={x} y={y} width={w} height={h} fill={palette[key]} />
        ))}
      </svg>
    </div>
  );
}

interface LoginViewProps {
  onLoginSuccess: (identity: AuthIdentity) => void;
}

/**
 * Sign-in form. No registration (accounts are bootstrapped operationally).
 * Holds credentials ONLY in transient form state — never in storage.
 */
function LoginView({ onLoginSuccess }: LoginViewProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    const trimmedUsername = username.trim();
    if (!trimmedUsername || !password) {
      setAuthError('Enter both username and password.');
      return;
    }
    setSubmitting(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: trimmedUsername, password }),
      });
      // clear credential bytes from memory as soon as the request is out
      setPassword('');
      if (res.ok) {
        const meRes = await fetch(`${API_BASE}/api/auth/me`, { credentials: 'include' });
        if (meRes.ok) {
          onLoginSuccess(await meRes.json());
          return;
        }
        setAuthError('Signed in, but session verification failed.');
      } else {
        let msg = `Sign-in failed (status ${res.status}).`;
        const ct = res.headers.get('content-type');
        if (ct && ct.includes('application/json')) {
          try {
            const errData = await res.json();
            msg = errData.detail || errData.error?.message || msg;
          } catch {}
        } else if (res.status === 401) {
          msg = 'Invalid username or password.';
        } else if (res.status === 403) {
          msg = 'Request forbidden or origin not allowed.';
        } else if (res.status === 429) {
          const retryAfter = res.headers.get('Retry-After');
          msg = `Too many attempts.${retryAfter ? ` Try again in ${retryAfter}s.` : ' Try again later.'}`;
        } else if (res.status === 503) {
          msg = 'Authentication service unavailable.';
        } else {
          try {
            const txt = await res.text();
            if (txt && !txt.trim().startsWith('<')) msg = txt;
          } catch {}
        }
        setAuthError(msg);
      }
    } catch {
      setAuthError('Unable to reach the authentication service.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex-1 w-full flex items-center justify-center py-20 px-8 bg-auth">
      <div className="w-full max-w-md bg-black/80 backdrop-blur border border-neutral-800 rounded shadow-2xl p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="flex justify-center">
            <div className="p-1 border border-white bg-black">
              <PhoenixMascot state="idle" size="md" />
            </div>
          </div>
          <h2 className="font-mono font-bold tracking-widest text-sm uppercase text-white">Investigator Sign-In</h2>
          <p className="text-[10px] text-neutral-400 font-mono tracking-wider">
            ACCESS TO FORENSIC TOOLS IS RESTRICTED TO AUTHORIZED PERSONNEL
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" aria-label="Investigator login">
          <div className="space-y-1">
            <label htmlFor="login-username" className="block text-[10px] font-mono uppercase tracking-wider text-neutral-400">
              Username
            </label>
            <input
              id="login-username"
              name="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 bg-neutral-900 border border-neutral-700 rounded text-sm font-mono text-white placeholder-neutral-600 focus:outline-none focus:border-white transition"
              placeholder="investigator id"
              disabled={submitting}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="login-password" className="block text-[10px] font-mono uppercase tracking-wider text-neutral-400">
              Password
            </label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-neutral-900 border border-neutral-700 rounded text-sm font-mono text-white placeholder-neutral-600 focus:outline-none focus:border-white transition"
              placeholder="••••••••••••"
              disabled={submitting}
            />
          </div>

          {authError && (
            <div role="alert" className="px-3 py-2 bg-red-950/60 border border-red-700/60 rounded text-xs font-mono text-red-200">
              {authError}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full px-6 py-3 bg-white hover:bg-neutral-200 disabled:bg-neutral-700 disabled:text-neutral-400 text-black font-mono text-xs uppercase font-bold tracking-widest rounded transition flex items-center justify-center gap-2"
          >
            {submitting ? <RefreshCw size={14} className="animate-spin" /> : <Lock size={14} />}
            {submitting ? 'Authenticating…' : 'Sign In'}
          </button>
        </form>

        <p className="text-[10px] text-neutral-500 font-mono text-center leading-relaxed">
          No public registration. Accounts are provisioned by the administrator
          via the secure bootstrap command.
        </p>
      </div>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState<'landing' | 'dashboard' | 'upload' | 'history' | 'login'>('landing');
  const [authUser, setAuthUser] = useState<AuthIdentity | null>(null);
  const [authResolved, setAuthResolved] = useState<AuthResolved>('unknown');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentScan, setCurrentScan] = useState<ScanResult | null>(null);

  const [history, setHistory] = useState<ScanItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // Archive filtering & sorting state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterVerdict, setFilterVerdict] = useState<string>('ALL');
  const [filterRisk, setFilterRisk] = useState<string>('ALL');
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest');

  // Dashboard specific state
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [dashboardScans, setDashboardScans] = useState<ScanItem[]>([]);
  const [dashboardLoading, setDashboardLoading] = useState<boolean>(false);

  // Sync hash navigation with activeTab
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (hash === 'login') {
        setActiveTab('login');
        setCurrentScan(null);
      } else if (hash === 'dashboard') {
        setActiveTab('dashboard');
        setCurrentScan(null);
      } else if (hash === 'upload') {
        setActiveTab('upload');
        setCurrentScan(null);
      } else if (hash === 'history') {
        setActiveTab('history');
        setCurrentScan(null);
      } else if (hash === 'landing' || !hash) {
        setActiveTab('landing');
        setCurrentScan(null);
      } else if (hash.startsWith('scan-')) {
        const scanId = hash.replace('scan-', '');
        if (scanId && (!currentScan || currentScan.scan_id !== scanId)) {
          fetchScanById(scanId, false);
        }
      }
    };

    if (window.location.hash) {
      handleHashChange();
    } else {
      window.location.hash = 'landing';
    }

    // Resolve authentication state once at startup (best-effort, no redirect
    // on network failure — backend may legitimately be momentarily offline).
    (async () => {
      try {
        const meRes = await fetch(`${API_BASE}/api/auth/me`, { credentials: 'include' });
        if (meRes.ok) {
          setAuthUser(await meRes.json());
          setAuthResolved('authed');
        } else if (meRes.status === 401) {
          setAuthResolved('guest');
        } else {
          setAuthResolved('unknown');
        }
      } catch {
        setAuthResolved('unknown');
      }
    })();

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Definitive-guest users may not stay on protected views (backend policy
  // already enforces this via 401; this is UX routing, NOT authorization).
  useEffect(() => {
    if (authResolved === 'guest' && activeTab !== 'landing' && activeTab !== 'login') {
      setActiveTab('login');
      window.location.hash = 'login';
    }
  }, [authResolved, activeTab]);

  const navigateToTab = (tab: 'landing' | 'dashboard' | 'upload' | 'history' | 'login') => {
    if (authResolved === 'guest' && tab !== 'landing' && tab !== 'login') {
      setActiveTab('login');
      window.location.hash = 'login';
      return;
    }
    setActiveTab(tab);
    setCurrentScan(null);
    window.location.hash = tab;
  };

  const handleSessionExpired = () => {
    setAuthUser(null);
    setAuthResolved('guest');
    setActiveTab('login');
    setCurrentScan(null);
    window.location.hash = 'login';
  };

  const handleLoginSuccess = (identity: AuthIdentity) => {
    setAuthUser(identity);
    setAuthResolved('authed');
    setActiveTab('dashboard');
    window.location.hash = 'dashboard';
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, { method: 'POST', credentials: 'include' });
    } catch {
      // network failure: local state is cleared regardless
    }
    setAuthUser(null);
    setAuthResolved('guest');
    setActiveTab('login');
    setCurrentScan(null);
    window.location.hash = 'login';
  };

  const loadHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data: HealthResponse = await res.json();
        setHealth(data);
      } else {
        throw new Error(`Health check returned status ${res.status}`);
      }
    } catch (err: any) {
      setHealthError(err.message || 'Failed to connect to health endpoint');
    } finally {
      setHealthLoading(false);
    }
  };

  const loadDashboardData = async () => {
    setDashboardLoading(true);
    try {
      const res = await authFetch(`${API_BASE}/api/scans?limit=20`, {}, { onSessionExpired: handleSessionExpired });
      if (res.ok) {
        const data = await res.json();
        setDashboardScans(data.scans || []);
      }
    } catch (err) {
      if (err instanceof SessionExpiredError) return; // already routed to login
      console.error('Failed to load dashboard scans sample', err);
    } finally {
      setDashboardLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'dashboard') {
      loadHealth();
      loadDashboardData();
    } else if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab]);

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await authFetch(`${API_BASE}/api/scans?limit=20`, {}, { onSessionExpired: handleSessionExpired });
      if (res.ok) {
        const data = await res.json();
        setHistory(data.scans || []);
      }
    } catch (err) {
      if (err instanceof SessionExpiredError) return; // already routed to login
      console.error('Failed to load history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const validateAndSetFile = (selectedFile: File) => {
    const maxBytes = 5 * 1024 * 1024; // 5 MiB = 5,242,880 bytes
    if (selectedFile.size > maxBytes) {
      setError('File exceeds the maximum allowed size of 5 MiB.');
      return;
    }
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(selectedFile.type)) {
      setError(`Unsupported image format (${selectedFile.type || 'unknown'}). Allowed: JPEG, PNG, WEBP.`);
      return;
    }
    setFile(selectedFile);
    setError(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (loading) return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await authFetch(`${API_BASE}/api/scans`, {
        method: 'POST',
        body: formData,
      }, { onSessionExpired: handleSessionExpired });

      if (!res.ok) {
        let errorMsg = `Analysis failed (status ${res.status})`;
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          try {
            const errData = await res.json();
            errorMsg = errData.error?.message || errData.detail || errorMsg;
          } catch {}
        } else {
          try {
            const text = await res.text();
            if (text && !text.trim().startsWith('<')) {
              errorMsg = text;
            } else if (res.status === 413) {
              errorMsg = 'File exceeds the maximum allowed size of 5 MiB.';
            } else if (res.status === 403) {
              errorMsg = 'Request forbidden or origin not allowed.';
            } else if (res.status === 401) {
              errorMsg = 'Unauthorized. Please sign in.';
            } else if (res.status >= 500) {
              errorMsg = 'Server error occurred during analysis.';
            }
          } catch {}
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();
      setCurrentScan(data.result);
      window.location.hash = `scan-${data.result.scan_id}`;
    } catch (err: any) {
      if (err instanceof SessionExpiredError) {
        setError(err.message);
      } else {
        setError(err.message || 'An unexpected error occurred during analysis.');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchScanById = async (scanId: string, updateHash: boolean = true) => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`${API_BASE}/api/scans/${scanId}`, {}, { onSessionExpired: handleSessionExpired });
      if (res.ok) {
        const data = await res.json();
        setCurrentScan(data);
        if (updateHash) {
          window.location.hash = `scan-${scanId}`;
        }
      } else if (res.status === 404) {
        throw new Error('Scan not found or you do not have access to it.');
      } else {
        throw new Error(`Failed to load scan (status ${res.status}).`);
      }
    } catch (err: any) {
      if (err instanceof SessionExpiredError) return; // already routed to login
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
      case 'ANALYSIS_FAILED':
        return <span className="px-2.5 py-1 bg-red-950 text-red-200 border border-red-700 rounded text-xs font-mono font-bold flex items-center gap-1.5"><XCircle size={13}/> ANALYSIS FAILED</span>;
      default:
        return <span className="px-2.5 py-1 bg-neutral-900 text-neutral-400 border border-neutral-700 rounded text-xs font-mono font-bold">UNKNOWN</span>;
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

  // Determine current Phoenix mascot state
  let phoenixState: PhoenixState = 'idle';
  if (loading) {
    phoenixState = 'processing';
  } else if (currentScan) {
    if (currentScan.verdict.label === 'LIKELY_AI') phoenixState = 'warning';
    else if (currentScan.verdict.label === 'LIKELY_REAL') phoenixState = 'reassuring';
    else if (currentScan.verdict.label === 'INCONCLUSIVE') phoenixState = 'inconclusive';
    else phoenixState = 'error';
  } else if (file) {
    phoenixState = 'investigating';
  }

  // Filter and sort archive items
  const filteredHistory = history.filter(item => {
    const matchesSearch = searchQuery === '' ||
      item.input.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.input.sha256.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesVerdict = filterVerdict === 'ALL' || item.verdict.label === filterVerdict;
    const matchesRisk = filterRisk === 'ALL' || (item.verdict.risk || '').toLowerCase() === filterRisk.toLowerCase();

    return matchesSearch && matchesVerdict && matchesRisk;
  }).sort((a, b) => {
    const dateA = new Date(a.created_at).getTime();
    const dateB = new Date(b.created_at).getTime();
    return sortOrder === 'newest' ? dateB - dateA : dateA - dateB;
  });

  // Compute breakdown statistics from dashboardScans sample
  const sampleSize = dashboardScans.length;
  let verdictCounts = { LIKELY_AI: 0, LIKELY_REAL: 0, INCONCLUSIVE: 0, ANALYSIS_FAILED: 0, unrecognized: 0 };
  let riskCounts = { low: 0, moderate: 0, high: 0, unknown: 0, unrecognized: 0 };

  dashboardScans.forEach(item => {
    const vLabel = item.verdict?.label;
    if (vLabel === 'LIKELY_AI') verdictCounts.LIKELY_AI++;
    else if (vLabel === 'LIKELY_REAL') verdictCounts.LIKELY_REAL++;
    else if (vLabel === 'INCONCLUSIVE') verdictCounts.INCONCLUSIVE++;
    else if (vLabel === 'ANALYSIS_FAILED') verdictCounts.ANALYSIS_FAILED++;
    else verdictCounts.unrecognized++;

    const rLevel = (item.verdict?.risk || '').toLowerCase();
    if (rLevel === 'low') riskCounts.low++;
    else if (rLevel === 'moderate') riskCounts.moderate++;
    else if (rLevel === 'high') riskCounts.high++;
    else if (rLevel === 'unknown') riskCounts.unknown++;
    else riskCounts.unrecognized++;
  });

  return (
    <div className="min-h-screen bg-[#090d16] text-white flex flex-col font-sans selection:bg-white selection:text-black">
      {/* Top Navbar */}
      <header className="border-b border-neutral-800 bg-[#090d16]/90 backdrop-blur sticky top-0 z-50 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigateToTab('landing')}>
          <div className="p-1 border border-white bg-black flex items-center justify-center">
            <PhoenixMascot state={phoenixState} size="sm" />
          </div>
          <div>
            <h1 className="font-mono font-bold tracking-widest text-sm uppercase text-white">PHANTOM PHOENIX</h1>
            <p className="text-[10px] text-neutral-400 font-mono tracking-wider">DIGITAL MEDIA FORENSICS & AUTHENTICITY</p>
          </div>
        </div>
        <nav className="flex items-center gap-3">
          {authResolved === 'authed' && authUser && (
            <span className="hidden md:inline-flex items-center gap-2 px-3 py-1.5 rounded border border-neutral-700 bg-neutral-900 text-[10px] font-mono uppercase tracking-wider text-neutral-300">
              <Lock size={12} /> {authUser.username} · {authUser.role}
            </span>
          )}
          {authResolved === 'authed' ? (
            <button
              onClick={handleLogout}
              className="px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition text-neutral-400 hover:text-white hover:bg-neutral-900"
              title="Clear the session cookie"
            >
              Logout
            </button>
          ) : (
            <button
              onClick={() => navigateToTab('login')}
              className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition flex items-center gap-2 ${activeTab === 'login' ? 'bg-white text-black font-bold' : 'bg-white/5 text-neutral-300 hover:text-white hover:bg-neutral-900'}`}
            >
              <Lock size={14} /> Sign In
            </button>
          )}
          <button
            onClick={() => navigateToTab('landing')}
            className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition ${activeTab === 'landing' && !currentScan ? 'bg-white text-black font-bold' : 'text-neutral-400 hover:text-white hover:bg-neutral-900'}`}
          >
            Home
          </button>
          <button
            onClick={() => navigateToTab('dashboard')}
            className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition flex items-center gap-2 ${activeTab === 'dashboard' && !currentScan ? 'bg-white text-black font-bold' : 'text-neutral-400 hover:text-white hover:bg-neutral-900'}`}
          >
            <Activity size={14} /> Dashboard
          </button>
          <button
            onClick={() => navigateToTab('upload')}
            className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition ${activeTab === 'upload' && !currentScan ? 'bg-white text-black font-bold' : 'text-neutral-400 hover:text-white hover:bg-neutral-900'}`}
          >
            New Scan
          </button>
          <button
            onClick={() => navigateToTab('history')}
            className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider transition flex items-center gap-2 ${activeTab === 'history' && !currentScan ? 'bg-white text-black font-bold' : 'text-neutral-400 hover:text-white hover:bg-neutral-900'}`}
          >
            <History size={14} /> Scan Archive
          </button>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full mx-auto flex flex-col">
        {/* Login View */}
        {activeTab === 'login' && (
          <LoginView onLoginSuccess={handleLoginSuccess} />
        )}

        {/* Landing View */}
        {activeTab === 'landing' && !currentScan && (
          <div className="flex-1 w-full bg-landing flex flex-col items-center justify-center py-20 px-8">
            <div className="max-w-5xl mx-auto w-full space-y-16">
              {/* Hero Section */}
              <div className="text-center space-y-6 max-w-3xl mx-auto bg-black/75 backdrop-blur p-10 border border-neutral-800 rounded shadow-2xl relative overflow-hidden">
                {/* Phoenix crest — hero presence, magic-ring stays axial */}
                <div className="flex justify-center pt-1">
                  <PhoenixMascot state="investigating" size="lg" ariaLabel="Phantom Phoenix, ever-watchful" />
                </div>
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-neutral-900 border border-neutral-700 text-xs font-mono text-neutral-300 rounded">
                  <Terminal size={14} className="text-white" /> Cyber-Forensic Intelligence Engine v2.4
                </div>
                <h2 className="text-3xl md:text-5xl font-mono uppercase tracking-wider text-white font-bold leading-tight">
                  Digital Media Authenticity & AI Forensic Intelligence
                </h2>
                <p className="text-neutral-300 text-sm font-mono leading-relaxed">
                  Verify visual media with rigorous computer vision and multi-layered forensic inspection. Powered by deep neural networks, cryptographic metadata auditing, and optical residual analysis.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
                  <button
                    onClick={() => navigateToTab('upload')}
                    className="px-6 py-3 bg-amber-400 hover:bg-amber-300 text-black font-mono text-xs uppercase font-bold tracking-widest rounded transition flex items-center gap-2 shadow-[0_0_12px_rgba(251,191,36,0.35)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300"
                  >
                    <Sparkles size={16} /> Start Investigation
                  </button>
                  <button
                    onClick={() => navigateToTab('dashboard')}
                    className="px-6 py-3 bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-700 font-mono text-xs uppercase tracking-wider rounded transition flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                  >
                    <Activity size={16} /> Investigator Dashboard
                  </button>
                </div>
              </div>

              {/* Feature Grid */}
              <div className="grid md:grid-cols-3 gap-6">
                <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-3">
                  <div className="p-3 bg-neutral-900 border border-neutral-700 rounded w-fit text-white">
                    <Cpu size={20} />
                  </div>
                  <h3 className="font-mono text-sm uppercase tracking-wider text-white font-bold">Vision Transformer Detection</h3>
                  <p className="text-xs font-mono text-neutral-400 leading-relaxed">
                    Evaluates image authenticity using state-of-the-art Vision Transformer (ViT-Small) deepfake detectors, returning precise fake probabilities and raw logit scores.
                  </p>
                </div>

                <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-3">
                  <div className="p-3 bg-neutral-900 border border-neutral-700 rounded w-fit text-white">
                    <Search size={20} />
                  </div>
                  <h3 className="font-mono text-sm uppercase tracking-wider text-white font-bold">Metadata & EXIF Audit</h3>
                  <p className="text-xs font-mono text-neutral-400 leading-relaxed">
                    Inspects cryptographic SHA-256 signatures, exact pixel dimensions, byte size allocations, and media type headers to ensure chain of custody.
                  </p>
                </div>

                <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-3">
                  <div className="p-3 bg-neutral-900 border border-neutral-700 rounded w-fit text-white">
                    <Layers size={20} />
                  </div>
                  <h3 className="font-mono text-sm uppercase tracking-wider text-white font-bold">Multi-Analyzer Forensics</h3>
                  <p className="text-xs font-mono text-neutral-400 leading-relaxed">
                    Executes Error Level Analysis (ELA) for compression discrepancies, noise residual extraction, and 2D FFT Frequency spectrum transforms.
                  </p>
                </div>

                <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-3">
                  <div className="p-3 bg-neutral-900 border border-neutral-700 rounded w-fit text-white">
                    <FileText size={20} />
                  </div>
                  <h3 className="font-mono text-sm uppercase tracking-wider text-white font-bold">Structured Evidence Cards</h3>
                  <p className="text-xs font-mono text-neutral-400 leading-relaxed">
                    Inspect normalized forensic evidence records with detailed analyzer interpretations, raw metrics, and generated visual artifacts.
                  </p>
                </div>

                <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-3">
                  <div className="p-3 bg-neutral-900 border border-neutral-700 rounded w-fit text-white">
                    <Download size={20} />
                  </div>
                  <h3 className="font-mono text-sm uppercase tracking-wider text-white font-bold">PDF Forensic Reports</h3>
                  <p className="text-xs font-mono text-neutral-400 leading-relaxed">
                    Generate and download publication-ready ReportLab PDF forensic dossiers instantly for offline archiving and case review.
                  </p>
                </div>

                <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-3">
                  <div className="p-3 bg-neutral-900 border border-neutral-700 rounded w-fit text-white">
                    <Database size={20} />
                  </div>
                  <h3 className="font-mono text-sm uppercase tracking-wider text-white font-bold">Persisted Scan Archive</h3>
                  <p className="text-xs font-mono text-neutral-400 leading-relaxed">
                    Review previously executed inspection records retrieved directly from PostgreSQL storage with complete metadata and verdicts.
                  </p>
                </div>
              </div>

              {/* Methodology & Limitations Section */}
              <div className="bg-black/85 backdrop-blur border border-neutral-800 p-8 rounded space-y-4">
                <div className="flex items-center gap-3 border-b border-neutral-800 pb-3">
                  <Lock size={18} className="text-neutral-400" />
                  <h3 className="font-mono text-xs uppercase tracking-widest text-white font-bold">Methodology & Forensic Scope</h3>
                </div>
                <div className="text-xs font-mono text-neutral-300 space-y-3 leading-relaxed">
                  <p>
                    <strong className="text-white">Probabilistic Assessment:</strong> Detector outputs represent neural network confidence scores and analytical indicators. They serve as investigative screening aids and do not constitute absolute proof of origin, authorship, or intent.
                  </p>
                  <p>
                    <strong className="text-white">What We Do Not Claim:</strong> PHANTOM PHOENIX explicitly does not claim exact generator model attribution, cryptographic provenance watermarking verification, or definitive legal proof.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Dedicated Investigator Dashboard View */}
        {activeTab === 'dashboard' && !currentScan && (
          <div className="flex-1 w-full bg-dashboard py-12 px-8">
            <div className="max-w-7xl mx-auto space-y-8">
              {/* Dashboard Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-neutral-800 pb-4 bg-black/70 p-6 rounded backdrop-blur">
                <div className="flex items-center gap-4">
                  <PhoenixMascot state="reassuring" size="lg" />
                  <div>
                    <h2 className="text-2xl font-mono uppercase tracking-wider text-white flex items-center gap-3">
                      Investigator Dashboard
                    </h2>
                    <p className="text-xs text-neutral-400 font-mono mt-1">Real-time system telemetry & forensic investigation telemetry</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => { loadHealth(); loadDashboardData(); }}
                    className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-700 rounded text-xs font-mono flex items-center gap-2 transition"
                  >
                    <RefreshCw size={14} className={healthLoading || dashboardLoading ? "animate-spin" : ""} /> Refresh Telemetry
                  </button>
                </div>
              </div>

              {/* Top Row: System Health & Action Hub */}
              <div className="grid md:grid-cols-3 gap-6">
                {/* System Health Widget (2 cols) */}
                <div className="md:col-span-2 bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-4">
                  <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                    <h3 className="font-mono text-xs uppercase tracking-wider text-white flex items-center gap-2">
                      <Zap size={16} className="text-neutral-400" /> System & Detector Health
                    </h3>
                    {healthLoading ? (
                      <span className="text-xs font-mono text-neutral-500 flex items-center gap-1.5"><RefreshCw size={12} className="animate-spin" /> Checking...</span>
                    ) : health ? (
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold flex items-center gap-1 ${health.status === 'ok' ? 'bg-emerald-950 text-emerald-300 border border-emerald-700' : 'bg-amber-950 text-amber-300 border border-amber-700'}`}>
                        {health.status === 'ok' ? <CheckCircle size={12} /> : <AlertTriangle size={12} />} Status: {health.status}
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-neutral-900 text-neutral-400 border border-neutral-700">Offline</span>
                    )}
                  </div>

                  {healthError ? (
                    <div className="p-4 bg-neutral-900 border border-neutral-800 rounded text-xs font-mono text-neutral-300 flex items-center justify-between">
                      <span>Error fetching health: {healthError}</span>
                      <button onClick={loadHealth} className="px-3 py-1 bg-white text-black rounded text-[11px] font-bold">Retry</button>
                    </div>
                  ) : health ? (
                    <div className="grid sm:grid-cols-2 gap-4 text-xs font-mono">
                      <div className="p-3 bg-neutral-900/90 rounded border border-neutral-800 space-y-1">
                        <span className="text-neutral-400 text-[10px] uppercase">Detector Model ID</span>
                        <p className="text-white font-bold truncate">{health.detector_model_id || 'Not configured'}</p>
                      </div>
                      <div className="p-3 bg-neutral-900/90 rounded border border-neutral-800 space-y-1">
                        <span className="text-neutral-400 text-[10px] uppercase">Detector Status</span>
                        <p className="text-white font-bold flex items-center gap-2">
                          {health.detector_loaded ? <span className="w-2 h-2 rounded-full bg-emerald-500"></span> : <span className="w-2 h-2 rounded-full bg-amber-500"></span>}
                          {health.detector_loaded ? 'Loaded & Active' : 'Unloaded / Lazy'}
                        </p>
                      </div>
                      <div className="p-3 bg-neutral-900/90 rounded border border-neutral-800 space-y-1">
                        <span className="text-neutral-400 text-[10px] uppercase">Hardware Acceleration</span>
                        <p className="text-white font-bold flex items-center gap-2">
                          {health.cuda_available ? <CheckCircle size={14} className="text-emerald-400" /> : <XCircle size={14} className="text-neutral-500" />}
                          {health.cuda_available ? (health.gpu_name || 'CUDA GPU Active') : 'CPU Mode'}
                        </p>
                      </div>
                      <div className="p-3 bg-neutral-900/90 rounded border border-neutral-800 space-y-1">
                        <span className="text-neutral-400 text-[10px] uppercase">API Version</span>
                        <p className="text-white font-bold">v{health.api_version}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="py-8 text-center text-neutral-500 font-mono text-xs">Loading system telemetry...</div>
                  )}
                </div>

                {/* Action Hub */}
                <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded flex flex-col justify-between space-y-4">
                  <div className="border-b border-neutral-800 pb-3">
                    <h3 className="font-mono text-xs uppercase tracking-wider text-white flex items-center gap-2">
                      <Sparkles size={16} className="text-neutral-400" /> Action Hub
                    </h3>
                  </div>
                  <p className="text-xs font-mono text-neutral-400 leading-relaxed">
                    Initiate a new forensic analysis scan or review persisted inspection records in the archive.
                  </p>
                  <div className="space-y-3 pt-2">
                    <button
                      onClick={() => navigateToTab('upload')}
                      className="w-full py-2.5 bg-white hover:bg-neutral-200 text-black font-mono text-xs uppercase font-bold tracking-wider rounded transition flex items-center justify-center gap-2"
                    >
                      <Upload size={14} /> Start New Scan
                    </button>
                    <button
                      onClick={() => navigateToTab('history')}
                      className="w-full py-2.5 bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-700 font-mono text-xs uppercase tracking-wider rounded transition flex items-center justify-center gap-2"
                    >
                      <History size={14} /> View Full Archive
                    </button>
                  </div>
                </div>
              </div>

              {/* Second Row: Verdict & Risk Breakdown (Recent Sample) */}
              <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <h3 className="font-mono text-xs uppercase tracking-wider text-white flex items-center gap-2">
                    <BarChart3 size={16} className="text-neutral-400" /> Verdict & Risk Breakdown (Recent Dataset Sample — {sampleSize} Records)
                  </h3>
                  <span className="text-[10px] font-mono text-neutral-500 uppercase">Sample Scope Only</span>
                </div>

                {dashboardLoading ? (
                  <div className="py-12 text-center text-neutral-500 font-mono text-xs">Calculating sample distribution...</div>
                ) : sampleSize === 0 ? (
                  <div className="py-12 text-center text-neutral-500 font-mono text-xs border border-dashed border-neutral-800 rounded">
                    No scan records in current sample to calculate distribution.
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-6 pt-2">
                    {/* Verdict Breakdown */}
                    <div className="space-y-3 p-4 bg-neutral-900/80 rounded border border-neutral-800">
                      <h4 className="text-xs font-mono uppercase text-neutral-300 font-bold border-b border-neutral-800 pb-2">Verdict Distribution</h4>
                      <div className="space-y-2 text-xs font-mono">
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300 flex items-center gap-2"><span className="w-2.5 h-2.5 rounded bg-white"></span> Likely AI-Generated</span>
                          <span className="font-bold text-white">{verdictCounts.LIKELY_AI} <span className="text-neutral-500 font-normal">({((verdictCounts.LIKELY_AI / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300 flex items-center gap-2"><span className="w-2.5 h-2.5 rounded bg-neutral-600"></span> Likely Authentic</span>
                          <span className="font-bold text-white">{verdictCounts.LIKELY_REAL} <span className="text-neutral-500 font-normal">({((verdictCounts.LIKELY_REAL / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300 flex items-center gap-2"><span className="w-2.5 h-2.5 rounded bg-amber-500"></span> Inconclusive</span>
                          <span className="font-bold text-white">{verdictCounts.INCONCLUSIVE} <span className="text-neutral-500 font-normal">({((verdictCounts.INCONCLUSIVE / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300 flex items-center gap-2"><span className="w-2.5 h-2.5 rounded bg-red-600"></span> Analysis Failed</span>
                          <span className="font-bold text-white">{verdictCounts.ANALYSIS_FAILED} <span className="text-neutral-500 font-normal">({((verdictCounts.ANALYSIS_FAILED / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        {verdictCounts.unrecognized > 0 && (
                          <div className="flex justify-between items-center text-neutral-500 pt-1 border-t border-neutral-800">
                            <span>Unrecognized / Other</span>
                            <span>{verdictCounts.unrecognized}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Risk Level Breakdown */}
                    <div className="space-y-3 p-4 bg-neutral-900/80 rounded border border-neutral-800">
                      <h4 className="text-xs font-mono uppercase text-neutral-300 font-bold border-b border-neutral-800 pb-2">Risk Level Distribution</h4>
                      <div className="space-y-2 text-xs font-mono">
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300">Low Risk</span>
                          <span className="font-bold text-white">{riskCounts.low} <span className="text-neutral-500 font-normal">({((riskCounts.low / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300">Moderate Risk</span>
                          <span className="font-bold text-white">{riskCounts.moderate} <span className="text-neutral-500 font-normal">({((riskCounts.moderate / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300">High Risk</span>
                          <span className="font-bold text-white">{riskCounts.high} <span className="text-neutral-500 font-normal">({((riskCounts.high / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-neutral-300">Unknown Risk</span>
                          <span className="font-bold text-white">{riskCounts.unknown} <span className="text-neutral-500 font-normal">({((riskCounts.unknown / sampleSize) * 100).toFixed(1)}%)</span></span>
                        </div>
                        {riskCounts.unrecognized > 0 && (
                          <div className="flex justify-between items-center text-neutral-500 pt-1 border-t border-neutral-800">
                            <span>Unrecognized / Other</span>
                            <span>{riskCounts.unrecognized}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Third Row: Recent Investigations (Latest 10) */}
              <div className="bg-black/80 backdrop-blur border border-neutral-800 p-6 rounded space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <h3 className="font-mono text-xs uppercase tracking-wider text-white flex items-center gap-2">
                    <History size={16} className="text-neutral-400" /> Recent Investigations (Latest {Math.min(10, dashboardScans.length)})
                  </h3>
                  <button
                    onClick={() => navigateToTab('history')}
                    className="text-xs font-mono text-neutral-400 hover:text-white underline transition"
                  >
                    View All in Archive →
                  </button>
                </div>

                {dashboardLoading ? (
                  <div className="py-12 text-center text-neutral-500 font-mono text-xs">Loading recent investigations...</div>
                ) : dashboardScans.length === 0 ? (
                  <div className="py-12 text-center border border-dashed border-neutral-800 rounded text-neutral-400 font-mono text-xs">
                    No recent forensic investigations found.
                    <div className="mt-4">
                      <button
                        onClick={() => navigateToTab('upload')}
                        className="px-4 py-2 bg-white text-black font-mono text-xs uppercase font-bold rounded"
                      >
                        Initiate First Scan
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {dashboardScans.slice(0, 10).map((item) => (
                      <div
                        key={item.scan_id}
                        onClick={() => fetchScanById(item.scan_id)}
                        className="p-4 bg-neutral-950/80 backdrop-blur border border-neutral-800 hover:border-neutral-600 rounded flex items-center justify-between cursor-pointer transition group"
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
            </div>
          </div>
        )}

        {/* History View with Search, Filters & Sorting */}
        {activeTab === 'history' && !currentScan && (
          <div className="flex-1 w-full bg-dashboard py-12 px-8">
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="flex flex-wrap justify-between items-center gap-4 border-b border-neutral-800 pb-4 bg-black/60 p-6 rounded backdrop-blur">
                <div className="flex items-center gap-4">
                  <PhoenixMascot state="idle" size="lg" />
                  <div>
                    <h2 className="text-xl font-mono uppercase tracking-wider text-white">Scan Archive</h2>
                    <p className="text-xs text-neutral-400 font-mono mt-1">Persisted forensic inspection records ({filteredHistory.length} of {history.length})</p>
                  </div>
                </div>
                <button
                  onClick={loadHistory}
                  className="px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-700 rounded text-xs font-mono flex items-center gap-1.5 transition"
                >
                  <RefreshCw size={12} className={historyLoading ? "animate-spin" : ""} /> Refresh
                </button>
              </div>

              {/* Filter, Search & Sort Toolbar */}
              <div className="bg-black/80 backdrop-blur border border-neutral-800 p-4 rounded grid md:grid-cols-4 gap-4">
                <div className="relative md:col-span-2">
                  <Search className="absolute left-3 top-2.5 text-neutral-500" size={16} />
                  <input
                    type="text"
                    placeholder="Search by filename or SHA-256..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-neutral-900 border border-neutral-700 rounded pl-10 pr-4 py-2 text-xs font-mono text-white placeholder-neutral-500 focus:outline-none focus:border-white"
                  />
                </div>

                <div>
                  <select
                    value={filterVerdict}
                    onChange={(e) => setFilterVerdict(e.target.value)}
                    className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-white"
                  >
                    <option value="ALL">All Verdicts</option>
                    <option value="LIKELY_AI">Likely AI-Generated</option>
                    <option value="LIKELY_REAL">Likely Authentic</option>
                    <option value="INCONCLUSIVE">Inconclusive</option>
                    <option value="ANALYSIS_FAILED">Analysis Failed</option>
                  </select>
                </div>

                <div className="flex gap-2">
                  <select
                    value={filterRisk}
                    onChange={(e) => setFilterRisk(e.target.value)}
                    className="flex-1 bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-white"
                  >
                    <option value="ALL">All Risks</option>
                    <option value="low">Low Risk</option>
                    <option value="moderate">Moderate Risk</option>
                    <option value="high">High Risk</option>
                    <option value="unknown">Unknown Risk</option>
                  </select>

                  <button
                    onClick={() => setSortOrder(sortOrder === 'newest' ? 'oldest' : 'newest')}
                    title={`Sort by timestamp (${sortOrder})`}
                    className="px-3 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-700 rounded text-xs font-mono flex items-center justify-center transition"
                  >
                    <ArrowUpDown size={14} />
                  </button>
                </div>
              </div>

              {historyLoading && history.length === 0 ? (
                <div className="py-20 text-center text-neutral-500 font-mono text-xs bg-black/60 rounded backdrop-blur">Loading records...</div>
              ) : filteredHistory.length === 0 ? (
                <div className="py-20 text-center border border-dashed border-neutral-800 rounded bg-black/60 backdrop-blur space-y-3">
                  <History size={32} className="mx-auto text-neutral-600 mb-3" />
                  <p className="text-neutral-400 font-mono text-xs">No scan records match your search or filter criteria.</p>
                  <button
                    onClick={() => { setSearchQuery(''); setFilterVerdict('ALL'); setFilterRisk('ALL'); }}
                    className="px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-700 rounded text-xs font-mono transition"
                  >
                    Clear Filters
                  </button>
                </div>
              ) : (
                <div className="grid gap-3">
                  {filteredHistory.map((item) => (
                    <div
                      key={item.scan_id}
                      onClick={() => fetchScanById(item.scan_id)}
                      className="p-4 bg-neutral-950/80 backdrop-blur border border-neutral-800 hover:border-neutral-600 rounded flex items-center justify-between cursor-pointer transition group"
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
          </div>
        )}

        {/* Upload View (Polished Milestone 9A) */}
        {(!currentScan && activeTab === 'upload') && (
          <div className="flex-1 w-full bg-upload-console flex items-center justify-center py-16 px-8">
            <div className="max-w-2xl mx-auto w-full space-y-8 bg-black/85 backdrop-blur p-8 border border-neutral-800 rounded shadow-2xl relative">
              <div className="absolute top-6 right-6">
                <PhoenixMascot state={phoenixState} size="lg" />
              </div>
              <div className="text-center space-y-3 pr-16">
                <h2 className="text-2xl font-mono uppercase tracking-widest text-white">Forensic Evidence Ingestion</h2>
                <p className="text-neutral-400 text-xs font-mono leading-relaxed max-w-lg mx-auto">
                  Upload image evidence (JPEG, PNG, WEBP). Pipeline executes Vision Transformer AI detection, EXIF/XMP inspection, Error Level Analysis (ELA), Noise residuals, and 2D FFT Frequency spectra.
                </p>
              </div>

              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                className={`border border-dashed ${loading ? 'opacity-60 cursor-not-allowed' : 'border-neutral-700 hover:border-white cursor-pointer'} bg-neutral-950/90 rounded p-8 text-center transition flex flex-col items-center justify-center relative`}
              >
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  disabled={loading}
                  className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                />

                {file ? (
                  <div className="space-y-4 w-full flex flex-col items-center">
                    <div className="w-32 h-32 rounded border border-neutral-700 overflow-hidden bg-black flex items-center justify-center">
                      <img
                        src={URL.createObjectURL(file)}
                        alt="Selected preview"
                        className="object-contain h-full w-full"
                      />
                    </div>
                    <div>
                      <h3 className="text-sm font-mono text-white font-bold">{file.name}</h3>
                      <p className="text-[11px] text-neutral-400 font-mono mt-0.5">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB • {file.type || 'image'}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 pt-2">
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setFile(null); setError(null); }}
                        disabled={loading}
                        className="px-3 py-1 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-700 rounded text-xs font-mono transition"
                      >
                        Remove / Replace File
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="p-3 border border-neutral-700 rounded text-neutral-300 mb-4 bg-neutral-900">
                      <Upload size={24} />
                    </div>
                    <h3 className="text-sm font-mono text-neutral-200 mb-1">
                      Drag & drop image here, or click to browse
                    </h3>
                    <p className="text-[11px] text-neutral-500 font-mono">
                      Supported: JPEG, PNG, WEBP • Max size: 15 MiB • Max dimensions: 8192px
                    </p>
                  </>
                )}
              </div>

              {error && (
                <div className="p-3 bg-red-950/80 border border-red-800 rounded text-red-200 text-xs font-mono flex items-center gap-3">
                  <AlertTriangle size={16} className="shrink-0 text-red-400" />
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
          </div>
        )}

        {/* Results View */}
        {currentScan && (
          <div className={`flex-1 w-full ${currentScan.verdict.label === 'LIKELY_AI' ? 'bg-results-warning' : 'bg-results-friendly'} py-12 px-8`}>
            <div className="max-w-7xl mx-auto space-y-6 bg-black/80 backdrop-blur p-8 border border-neutral-800 rounded">
            {/* Top Bar for Results */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-neutral-950/90 border border-neutral-800 p-6 rounded relative">
              <div className="absolute top-4 right-6">
                <PhoenixMascot state={phoenixState} size="lg" />
              </div>
              <div className="pr-20">
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
                  onClick={() => { setCurrentScan(null); navigateToTab('upload'); }}
                  className="px-4 py-2 bg-white text-black hover:bg-neutral-200 rounded text-xs font-mono uppercase font-bold tracking-wider transition"
                >
                  New Scan
                </button>
              </div>
            </div>

            {/* AI Detector & Verdict Rationale */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-neutral-950/90 border border-neutral-800 p-6 rounded space-y-4">
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

              <div className="bg-neutral-950/90 border border-neutral-800 p-6 rounded space-y-4">
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
                  <div key={ev.id} className="bg-neutral-950/90 border border-neutral-800 p-5 rounded space-y-3">
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
