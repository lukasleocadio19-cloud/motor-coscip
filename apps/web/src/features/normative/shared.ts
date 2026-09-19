/** Tipos e utilitários da base normativa (fontes, pacotes e cobertura por documento). */

export interface SourceRow {
  id: string;
  document: string;
  title: string;
  edition: string | null;
  url: string | null;
  pdf_sha256: string | null;
  text_sha256: string;
  collected_at: string | null;
  items: number | null;
  current: boolean;
  created_at: string;
}

export interface Citation {
  document: string;
  item: string;
  verified: boolean;
  page: number | null;
  excerpt: string;
  missing_terms: string[];
  problem: string | null;
}

export interface PackageRule {
  rule_id: string;
  version: number;
  title: string;
  measure: string;
  subject: string;
  citations: Citation[];
}

export interface CoverageItem {
  document: string;
  item: string;
  topic: string;
  reason: string;
  citation: Citation;
}

export interface PackageSummary {
  id: string;
  name: string;
  jurisdiction: string;
  state: string;
  content_sha256: string;
  verified: boolean;
  rules: number;
  package: { id: string; version: number } | null;
  created_at: string;
}

export interface PackageDetail extends Omit<PackageSummary, "rules"> {
  manifest: {
    rules: PackageRule[];
    coverage: CoverageItem[];
    sources: { document: string; text_sha256: string }[];
    symbols_citation: Citation | Citation[] | null;
    sources_sha256: string;
  };
}

export const GROUPS: { key: string; label: string }[] = [
  { key: "1", label: "Grupo 1 — Generalidades" },
  { key: "2", label: "Grupo 2 — Medidas de segurança" },
  { key: "3", label: "Grupo 3 — Riscos específicos" },
  { key: "4", label: "Grupo 4 — Estruturas especiais" },
  { key: "5", label: "Grupo 5 — Eventos" },
  { key: "L", label: "Legislação" },
];

export function groupOf(document: string): string {
  const m = document.match(/^NT (\d)-/);
  return m ? m[1] : "L";
}

/** Ordem natural: NT 1-01 P1 < NT 1-01 P2 < NT 1-02 … */
export function compareDocs(a: string, b: string) {
  return a.localeCompare(b, "pt-BR", { numeric: true });
}

export interface DocCoverage {
  rules: { rule: PackageRule; citation: Citation }[];
  manual: CoverageItem[];
  dictionary: boolean;
}

export function coverageByDocument(pkg: PackageDetail | undefined): Map<string, DocCoverage> {
  const out = new Map<string, DocCoverage>();
  const get = (doc: string) => {
    let c = out.get(doc);
    if (!c) {
      c = { rules: [], manual: [], dictionary: false };
      out.set(doc, c);
    }
    return c;
  };
  if (!pkg) return out;
  for (const rule of pkg.manifest.rules ?? []) {
    for (const citation of rule.citations ?? []) get(citation.document).rules.push({ rule, citation });
  }
  for (const item of pkg.manifest.coverage ?? []) get(item.citation?.document ?? item.document).manual.push(item);
  const sym = pkg.manifest.symbols_citation;
  for (const c of Array.isArray(sym) ? sym : sym ? [sym] : []) get(c.document).dictionary = true;
  return out;
}

export function shortHash(h: string | null | undefined, n = 12) {
  return h ? `${h.slice(0, n)}…` : "—";
}

export function fmtDate(iso: string | null | undefined) {
  return iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—";
}
