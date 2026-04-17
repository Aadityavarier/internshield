const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const RESULT_CACHE_PREFIX = "internshield_result_";

export interface DimensionScores {
  rules: number;
  nlp: number;
  ner: number;
}

export interface TriggeredFlag {
  rule: string;
  severity: "critical" | "high" | "medium" | "low";
  message: string;
  score: number;
}

export interface AnalysisResult {
  id: string;
  confidence_score: number;
  verdict: "likely_genuine" | "suspicious" | "likely_fake";
  dimension_scores: DimensionScores;
  triggered_flags: TriggeredFlag[];
  next_steps: string[];
  company_name: string | null;
  input_type: "pdf" | "image" | "text";
  extraction_method: string;
  processing_time_ms: number;
}

export interface ScanRecord {
  id: string;
  created_at: string;
  confidence_score: number;
  verdict: string;
  company_name: string | null;
  input_type: string;
}

export interface FullScanRecord extends ScanRecord {
  extracted_text: string;
  dimension_scores: DimensionScores;
  triggered_flags: TriggeredFlag[];
  next_steps: string[];
  extraction_method: string;
  processing_time_ms: number;
}

export interface CompanyDetails {
  companyName?: string;
  companyWebsite?: string;
  contactEmail?: string;
}

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sessionId = localStorage.getItem("internshield_session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("internshield_session_id", sessionId);
  }
  return sessionId;
}

export async function analyzeDocument(
  file: File | null,
  text: string | null,
  details?: CompanyDetails
): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("session_id", getSessionId());

  if (file) {
    formData.append("file", file);
  }
  if (text) {
    formData.append("text", text);
  }

  // Append optional enrichment fields
  if (details?.companyName) {
    formData.append("company_name_input", details.companyName);
  }
  if (details?.companyWebsite) {
    formData.append("company_website", details.companyWebsite);
  }
  if (details?.contactEmail) {
    formData.append("contact_email", details.contactEmail);
  }

  if (!file && !text) {
    throw new Error("Please provide a file or text to analyze");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error(
      "Could not connect to the analysis server. Please make sure the backend is running (uvicorn main:app --reload --port 8000)."
    );
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Analysis failed (${response.status})`);
  }

  const result: AnalysisResult = await response.json();

  // Cache result in sessionStorage for fallback
  cacheResult(result);

  return result;
}

export async function getHistory(): Promise<ScanRecord[]> {
  const sessionId = getSessionId();
  if (!sessionId) return [];

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/history/${sessionId}`
    );
    if (!response.ok) return [];
    const data = await response.json();
    return data.scans || [];
  } catch {
    return [];
  }
}

export async function getResult(scanId: string): Promise<FullScanRecord> {
  const response = await fetch(
    `${API_BASE_URL}/api/result/${scanId}`
  );

  if (!response.ok) {
    throw new Error("Result not found");
  }

  return response.json();
}

export function getVerdictInfo(verdict: string) {
  switch (verdict) {
    case "likely_genuine":
      return {
        label: "Likely Genuine",
        emoji: "✅",
        color: "var(--accent-500)",
        badgeClass: "badge-genuine",
        gradient: "var(--gradient-genuine)",
      };
    case "suspicious":
      return {
        label: "Suspicious",
        emoji: "⚠️",
        color: "var(--warning-500)",
        badgeClass: "badge-suspicious",
        gradient: "var(--gradient-suspicious)",
      };
    case "likely_fake":
      return {
        label: "Likely Fake",
        emoji: "🚨",
        color: "var(--danger-500)",
        badgeClass: "badge-fake",
        gradient: "var(--gradient-fake)",
      };
    default:
      return {
        label: "Unknown",
        emoji: "❓",
        color: "var(--text-secondary)",
        badgeClass: "",
        gradient: "var(--gradient-primary)",
      };
  }
}

/** Cache a result in sessionStorage for offline/no-Supabase fallback */
function cacheResult(result: AnalysisResult): void {
  if (typeof window === "undefined") return;
  try {
    const record: FullScanRecord = {
      ...result,
      created_at: new Date().toISOString(),
      extracted_text: "",
    };
    sessionStorage.setItem(
      `${RESULT_CACHE_PREFIX}${result.id}`,
      JSON.stringify(record)
    );
  } catch {
    // sessionStorage might be full or unavailable
  }
}

/** Try to get a cached result from sessionStorage */
export function getCachedResult(scanId: string): FullScanRecord | null {
  if (typeof window === "undefined") return null;
  try {
    const cached = sessionStorage.getItem(`${RESULT_CACHE_PREFIX}${scanId}`);
    if (cached) {
      return JSON.parse(cached) as FullScanRecord;
    }
  } catch {
    // ignore
  }
  return null;
}
