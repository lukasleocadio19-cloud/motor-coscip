/** Contratos das rotas de análise automática da planta (plant-analyses). */

export type Risk = "PEQUENO" | "MEDIO" | "GRANDE";

export interface PlantContext {
  risk_class: Risk | null;
  unifamiliar: boolean;
  occupancy: string | null;
  requires_hydrants: boolean | null;
  requires_alarm: boolean | null;
  requires_lighting: boolean | null;
  exit_max_distance_m: number | null;
  exits_confirmed: boolean;
  risk_basis?: string | null;
}

export interface Division {
  id: string;
  group: string;
  description: string;
  risk: string;
  page: number | null;
  merged_from: string | null;
}

export interface PlantOptions {
  packages: { id: string; name: string; state: string; rules: number; created_at: string }[];
  classes: { id: string; label: string }[];
  floors: { id: string; name: string }[];
  layers: { name: string; segments: number; suggested_obstacle: boolean }[];
  classification: {
    source: { document: string; item: string };
    risk_to_rules: Record<string, Risk>;
    notes: string[];
    divisions: Division[];
  } | null;
}

export interface DrawingInfo {
  id: string;
  revision_id: string;
  file: string | null;
  unit: { confirmed: boolean; unit: string | null; scale_to_m: string | null };
  floors: { id: string; name: string }[];
}

export interface PlantAnalysis {
  id: string;
  state: string;
  drawing_id: string;
  rule_package_id: string;
  created_at: string;
  context: PlantContext | null;
  summary: { by_status: Record<string, number>; regions: number; plan_regions: number } | null;
  warnings: string[];
  duration_s: number | null;
  execution: { state: string; stage: string | null; error_code: string | null } | null;
  analysis_artifact_url: string | null;
  reports: { id: string; sha256: string; created_at: string; content_url: string; reviewed: number }[];
}

export interface Citation {
  document: string;
  item: string;
  page: number | null;
  verified: boolean;
  excerpt: string;
}

export interface RuleResult {
  rule_id: string;
  rule_version_id: string;
  title: string;
  measure: string;
  subject_type: "FLOOR" | "SYMBOL" | "ROOM";
  subject_id: string;
  subject_label: string;
  region_id: string;
  region_name: string;
  status: "PASS" | "FAIL" | "REVIEW_REQUIRED" | "NOT_APPLICABLE" | "MISSING_DATA";
  reason_code: string;
  trace: {
    measured?: number | string | boolean;
    uncertainty_abs?: number;
    required?: string;
    unit?: string;
    indicative?: string;
    gate?: string;
    missing?: string[];
    required_steps?: string[];
  };
  citations: Citation[];
}

export interface Region {
  id: string;
  name: string;
  source: "FLOOR" | "AUTO" | string;
  confirmed: boolean;
  kind: "PLAN" | "OTHER" | string;
  notes: string[];
  counts: Record<string, number>;
  skipped?: string;
  map_svg?: string;
  facts?: Record<string, { value: unknown; uncertainty: number | null }>;
  coverage?: Record<string, { label: string; sources: number; max_travel_m: number | null; uncertainty_m: number | null; unreachable_m2: number }>;
  area_checks?: { label: string; declared_m2: number; computed_m2: number | null; difference_m2: number | null; status: "CONFERE" | "DIVERGE" | "SEM_CONTORNO" }[];
}

export interface AnalysisJson {
  drawing: { sha256: string; scale_to_m: number; entity_count: number; segment_count: number };
  obstacles: { source: string; layers: string[]; segments: number };
  symbol_totals: Record<string, number>;
  legend_symbols: unknown[];
  symbols_outside_regions: unknown[];
  unrecognized_blocks: { block: string; layer: string; count: number }[];
  regions: Region[];
  results: RuleResult[];
  warnings: string[];
  duration_s: number;
}

export interface ReviewDecision {
  id: string;
  decision: "CONFIRM" | "CONTEST" | "REQUEST_DATA" | "RESOLVED_BY_NEW_REVISION";
  final_status: "PASS" | "FAIL" | "NOT_APPLICABLE" | null;
  justification: string;
  created_at: string | null;
}

export interface ReviewItem {
  result_id: string;
  status: string;
  decisions: ReviewDecision[];
}

/** Mesma chave do servidor: regra|sujeito|região (cortes da gravação em rule_results). */
export function reviewKey(r: RuleResult) {
  return `${r.rule_version_id}|${r.subject_id.slice(0, 36)}|${r.region_id.slice(0, 100)}`;
}

export const TERMINAL = new Set(["SUCCEEDED", "FAILED", "CANCELLED", "PARTIAL"]);

export const CLASS_LABELS: Record<string, string> = {
  EXTINTOR: "Extintores", HIDRANTE: "Hidrantes", MANGOTINHO: "Mangotinhos",
  HIDRANTE_URBANO: "Hidrante urbano", REGISTRO_RECALQUE: "Registro de recalque",
  BOMBA_INCENDIO: "Bombas de incêndio", ACIONADOR_BOMBA: "Acionador de bomba",
  RESERVA_TECNICA: "Reserva técnica", SPRINKLER: "Sprinklers",
  ILUMINACAO_EMERGENCIA: "Iluminação de emergência", DETECTOR: "Detectores",
  ACIONADOR_MANUAL: "Acionadores manuais", AVISADOR: "Avisadores",
  CENTRAL_ALARME: "Central de alarme", CENTRAL_GLP: "Central de GLP",
  SAIDA: "Saídas (marcações)", SINALIZACAO: "Placas de sinalização",
};

export const REASONS: Record<string, string> = {
  MEASURED_INTERVAL_SATISFIES: "medida (com incerteza) atende ao limite",
  MEASURED_INTERVAL_VIOLATES: "medida (com incerteza) não atende ao limite",
  UNCERTAINTY_CROSSES_LIMIT: "a incerteza atravessa o limite",
  QUALITY_GATE_NOT_MET: "condição de qualidade não atendida",
  HEURISTIC_EVIDENCE_VIOLATES: "evidência heurística indica falta; conferir",
  REQUIRED_INPUT_MISSING: "dado necessário ausente",
  REQUIRED_TABLE_KEY_UNKNOWN: "enquadramento necessário não informado",
  APPLICABILITY_FALSE: "condição de aplicação não ocorre",
  APPLICABILITY_UNKNOWN: "aplicabilidade não determinada",
  INPUT_CONFLICT: "dados conflitantes",
  UNCERTAINTY_UNKNOWN: "incerteza desconhecida",
};

export const GATES: Record<string, string> = {
  "quality.region_confirmed": "região automática (pavimento não recortado pelo analista)",
  "quality.walls_detected": "paredes não reconhecidas por layer",
  "quality.extinguisher.complete": "há área sem acesso a extintor pelo modelo de paredes",
  "quality.hydrant.complete": "há área sem acesso a hidrante pelo modelo de paredes",
  "quality.manual_call_point.complete": "há área sem acesso a acionador",
  "quality.exit.complete": "há área sem acesso a saída",
  "context.exits_confirmed": "saídas não confirmadas pelo analista",
  "quality.extinguisher.not_presumed": "extintor presumido pela placa E-5 + E-17 (sem símbolo)",
};

export const STATUS_ORDER = ["FAIL", "REVIEW_REQUIRED", "MISSING_DATA", "PASS", "NOT_APPLICABLE"] as const;

export function num(v: unknown, digits = 2) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "sim" : "não";
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return Number.isInteger(n) ? String(n) : n.toLocaleString("pt-BR", { maximumFractionDigits: digits });
}
