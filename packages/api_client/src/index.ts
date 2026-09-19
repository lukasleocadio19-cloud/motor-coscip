/**
 * Cliente da API local /v1. Mesma origem, cookie de sessão HttpOnly e
 * cabeçalho CSRF (double-submit). Tipos completos: `npm run gen:api` gera
 * `schema.d.ts` a partir do OpenAPI do backend.
 */

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  code: string;
  trace_id?: string;
  resource_id?: string | null;
  required_action?: string | null;
}

export class ApiError extends Error {
  constructor(public problem: ProblemDetail) {
    super(problem.title);
  }
}

function csrfToken(): string {
  const m = document.cookie.match(/(?:^|;\s*)coscip_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

export async function api<T>(
  path: string,
  init: RequestInit & { json?: unknown; idempotencyKey?: string; ifMatch?: number } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const method = (init.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") headers.set("X-CSRF-Token", csrfToken());
  if (init.idempotencyKey) headers.set("Idempotency-Key", init.idempotencyKey);
  if (init.ifMatch !== undefined) headers.set("If-Match", String(init.ifMatch));
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`/v1${path}`, { ...init, method, headers, body, credentials: "same-origin" });
  if (!res.ok) {
    const problem = (await res.json().catch(() => ({
      type: "about:blank", title: res.statusText, status: res.status, code: "HTTP_ERROR",
    }))) as ProblemDetail;
    throw new ApiError(problem);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

/** Troca o token de uso único do launcher (no fragmento da URL) por sessão. */
export async function exchangeLaunchToken(): Promise<boolean> {
  const m = window.location.hash.match(/launch=([\w-]+)/);
  if (!m) return false;
  history.replaceState(null, "", window.location.pathname); // limpa URL/histórico
  await api<void>("/local/session/exchange", { method: "POST", json: { token: m[1] } });
  return true;
}

export async function sha256Hex(data: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Upload em partes numeradas com checksum por parte. */
export async function uploadFile(
  revisionId: string,
  file: File,
  role: "ANALYTIC_DXF" | "XREF_DXF" | "SOURCE_DWG" | "DOCUMENT",
  onProgress?: (sent: number, total: number) => void,
): Promise<{ file_id: string; sha256: string; size: number; state: string }> {
  const session = await api<{ id: string; max_part_bytes: number }>(
    `/revisions/${revisionId}/uploads`,
    { method: "POST", json: { filename: file.name, role, size: file.size } },
  );
  const partSize = Math.min(session.max_part_bytes, 8 * 1024 * 1024);
  let n = 1;
  for (let off = 0; off < file.size; off += partSize, n++) {
    const chunk = await file.slice(off, off + partSize).arrayBuffer();
    await api(`/uploads/${session.id}/parts/${n}`, {
      method: "PUT",
      body: chunk,
      headers: { "X-Part-SHA256": await sha256Hex(chunk), "Content-Type": "application/octet-stream" },
    });
    onProgress?.(Math.min(off + partSize, file.size), file.size);
  }
  return api(`/uploads/${session.id}/complete`, { method: "POST" });
}

// --- tipos mínimos até a geração a partir do OpenAPI -----------------------
export type EvaluationStatus = "PASS" | "FAIL" | "REVIEW_REQUIRED" | "NOT_APPLICABLE" | "MISSING_DATA";
export type ExecutionState =
  | "CREATED" | "QUEUED" | "RUNNING" | "CANCEL_REQUESTED" | "SUCCEEDED"
  | "PARTIAL" | "WAITING_INPUT" | "FAILED" | "CANCELLED";

export interface Project {
  id: string;
  name: string;
  external_ref: string | null;
  address: string | null;
  responsible: string | null;
  row_version: number;
  created_at: string;
}

export interface Revision {
  id: string;
  number: number;
  state: "DRAFT" | "SEALED";
  manifest_sha256?: string | null;
}

export interface ExecutionOut {
  execution_id: string;
  kind: string;
  state: ExecutionState;
  stage: string | null;
  error_code: string | null;
  progress: { completed_stages: number; planned_stages: number };
}

export interface LocalStatus {
  status: string;
  version: string;
  data_dir_label: string;
  queue: { active_or_waiting: number };
  last_verified_backup_at: string | null;
  free_disk_bytes: number;
  ai_enabled: boolean;
}
