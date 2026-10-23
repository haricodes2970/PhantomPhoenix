export type VerdictLabel = "LIKELY_AI" | "LIKELY_REAL" | "INCONCLUSIVE" | "ANALYSIS_FAILED";
export type RiskLevel = "low" | "moderate" | "high" | "unknown";

export interface InputDetails {
  sha256: string;
  filename: string;
  media_type: string;
  byte_size: number;
  width: number;
  height: number;
}

export interface ModelOutput {
  model_id: string;
  model_revision: string;
  role: string;
  status: string;
  fake_probability: number | null;
  raw_logit: number | null;
  threshold_policy: string;
  limitations: string[];
  device: string | null;
  duration_seconds: number | null;
}

export interface Indicator {
  id: string;
  method: string;
  status: string;
  value: {
    result?: Record<string, any>;
    evidence_category?: string;
    limitations?: string[];
    error?: string | null;
  };
  note: string;
  artifact?: string | null;
}

export interface NormalizedEvidenceItem {
  id: string;
  source: string;
  method: string;
  status: string;
  evidence_category: string;
  result: Record<string, any>;
  interpretation: string;
  limitations: string[];
  artifact?: string | null;
}

export interface Verdict {
  label: VerdictLabel;
  risk: RiskLevel;
  rationale: string[];
  not_claimed: string[];
}

export interface ScanResult {
  scan_id: string;
  created_at: string;
  status: string;
  input: InputDetails;
  models: ModelOutput[];
  indicators: Indicator[];
  evidence_items: NormalizedEvidenceItem[];
  verdict: Verdict;
  error?: string | null;
}

export interface ScanItem {
  scan_id: string;
  created_at: string;
  status: string;
  input: InputDetails;
  verdict: Verdict;
}

export interface HealthResponse {
  status: string;
  api_version: string;
  detector_loaded: boolean;
  detector_model_id: string | null;
  cuda_available: boolean;
  gpu_name: string | null;
}
