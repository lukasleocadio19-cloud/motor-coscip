import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@coscip/api-client";
import { Button, Card, ErrorState, ExecutionBadge, StatusBadge } from "@coscip/ui";

import {
  type AnalysisJson, CLASS_LABELS, GATES, num, type PlantAnalysis, REASONS, type Region,
  type RuleResult, STATUS_ORDER, TERMINAL,
} from "./types";

const SUBJECT: Record<string, string> = { FLOOR: "Pavimento", SYMBOL: "Símbolo", ROOM: "Ambiente" };

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`Falha ao ler o resultado (${res.status})`);
  return (await res.json()) as T;
}

export function AnalysisResult({ analysisId, classes, onMap }: {
  analysisId: string;
  classes: { id: string; label: string }[];
  onMap: (block: string) => void;
}) {
  const qc = useQueryClient();
  const analysis = useQuery({
    queryKey: ["plant-analysis", analysisId],
    queryFn: () => api<PlantAnalysis>(`/plant-analyses/${analysisId}`),
    refetchInterval: (q) => (q.state.data && TERMINAL.has(q.state.data.state) ? false : 1500),
  });
  const a = analysis.data;
  const data = useQuery({
    queryKey: ["plant-analysis-json", analysisId],
    queryFn: () => fetchJson<AnalysisJson>(a!.analysis_artifact_url!),
    enabled: !!a?.analysis_artifact_url,
    staleTime: Infinity,
  });
  const reissue = useMutation({
    mutationFn: () => api(`/plant-analyses/${analysisId}/reports`, { method: "POST" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["plant-analysis", analysisId] }),
  });

  const [regionId, setRegionId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const regions = useMemo(() => {
    const rs = data.data?.regions ?? [];
    // Plantas de PPCI primeiro; entre elas, a de mais símbolos de segurança.
    const total = (r: Region) => Object.values(r.counts).reduce((a, b) => a + b, 0);
    return [...rs].sort((x, y) => Number(y.kind === "PLAN") - Number(x.kind === "PLAN") || total(y) - total(x));
  }, [data.data]);
  const region = regions.find((r) => r.id === regionId) ?? regions[0];

  if (analysis.error) return <ErrorState error={analysis.error} />;
  if (!a) return <p className="text-sm text-slate-500">Carregando análise…</p>;

  const running = !TERMINAL.has(a.state);
  const report = a.reports[0];

  return (
    <Card title="Resultado da análise">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <ExecutionBadge state={a.state} />
        {running && <span className="text-sm text-slate-600">{a.execution?.stage ?? "Na fila"}…</span>}
        {a.duration_s != null && <span className="text-xs text-slate-500">{num(a.duration_s, 1)} s</span>}
        {a.execution?.error_code && <span className="text-sm text-red-800">Erro: {a.execution.error_code}</span>}
        <span className="ml-auto flex flex-wrap gap-2">
          {report && (
            <a href={report.content_url} target="_blank" rel="noopener" className="rounded-md bg-teal-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-800">
              Abrir relatório ↗
            </a>
          )}
          {a.state === "SUCCEEDED" && (
            <Button variant="ghost" onClick={() => reissue.mutate()} disabled={reissue.isPending}>
              {reissue.isPending ? "Emitindo…" : "Nova emissão do relatório"}
            </Button>
          )}
          {a.analysis_artifact_url && (
            <a href={a.analysis_artifact_url} download={`analise-${a.id}.json`} className="rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-300">
              analysis.json
            </a>
          )}
        </span>
      </div>
      {reissue.error && <ErrorState error={reissue.error} />}

      {a.summary && (
        <div className="mb-4 flex flex-wrap gap-2">
          {STATUS_ORDER.filter((s) => a.summary!.by_status[s]).map((s) => (
            <button key={s} onClick={() => setStatusFilter(statusFilter === s ? "" : s)}
              className={`flex items-center gap-1 rounded ${statusFilter === s ? "ring-2 ring-teal-700" : ""}`}
              aria-pressed={statusFilter === s}>
              <StatusBadge status={s} />
              <span className="text-sm font-semibold tabular-nums">{a.summary!.by_status[s]}</span>
            </button>
          ))}
          <span className="self-center text-xs text-slate-500">
            {a.summary.plan_regions} planta(s) analisada(s) de {a.summary.regions} região(ões)
          </span>
        </div>
      )}
      <p className="mb-4 rounded bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-amber-600/30">
        Regras em rascunho, sem homologação técnica: resultado indicativo, sem valor normativo.
      </p>

      {a.warnings.length > 0 && (
        <ul className="mb-4 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
          {a.warnings.map((w) => <li key={w}>{w}</li>)}
        </ul>
      )}

      {data.isLoading && <p className="text-sm text-slate-500">Carregando mapas e resultados…</p>}
      {data.error && <ErrorState error={data.error} />}
      {data.data && (
        <>
          {regions.length > 1 && (
            <div role="tablist" className="mb-3 flex flex-wrap gap-1 border-b border-slate-200">
              {regions.map((r) => (
                <button key={r.id} role="tab" aria-selected={r.id === region?.id} onClick={() => setRegionId(r.id)}
                  className={`-mb-px rounded-t px-3 py-1.5 text-sm ${r.id === region?.id ? "border border-b-white border-slate-200 bg-white font-semibold" : "text-slate-600 hover:text-slate-900"}`}>
                  {r.name}{r.kind !== "PLAN" && <span className="text-xs text-slate-400"> (sem PPCI)</span>}
                </button>
              ))}
            </div>
          )}
          {region && (
            <RegionView
              region={region}
              results={data.data.results.filter((r) => r.region_id === region.id && (!statusFilter || r.status === statusFilter))}
            />
          )}
          <Unrecognized data={data.data} classes={classes} onMap={onMap} />
        </>
      )}
    </Card>
  );
}

function RegionView({ region, results }: { region: Region; results: RuleResult[] }) {
  const svg = useMemo(
    () => (region.map_svg ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(region.map_svg)}` : null),
    [region.map_svg],
  );
  const sorted = [...results].sort(
    (x, y) => STATUS_ORDER.indexOf(x.status) - STATUS_ORDER.indexOf(y.status) || x.title.localeCompare(y.title),
  );
  const area = region.facts?.["floor.area_m2"];
  const [big, setBig] = useState(false);
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className={big ? "xl:col-span-2" : ""}>
        <p className="mb-2 text-sm text-slate-600">
          {region.source === "AUTO" ? "Região automática (não confirmada)" : "Pavimento recortado pelo analista"}
          {area && <> · área útil {num(area.value)} m²</>}
        </p>
        {region.skipped && <p className="text-sm text-slate-500">Não analisada: {region.skipped}.</p>}
        {svg && (
          <figure>
            <img src={svg} alt={`Mapa de ${region.name}: interior, símbolos e piores percursos`}
              className="w-full rounded border border-slate-200 bg-white" />
            <figcaption className="mt-1 text-right">
              <button className="text-xs text-teal-800 underline" onClick={() => setBig(!big)}>
                {big ? "Reduzir mapa" : "Ampliar mapa"}
              </button>
            </figcaption>
          </figure>
        )}
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
          {Object.entries(region.counts).map(([cls, n]) => (
            <div key={cls} className="flex justify-between gap-2 border-b border-slate-100">
              <dt className="text-slate-600">{CLASS_LABELS[cls] ?? cls}</dt>
              <dd className="font-medium tabular-nums">{n}</dd>
            </div>
          ))}
        </dl>
        {region.coverage && (
          <table className="mt-3 w-full text-sm">
            <caption className="mb-1 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Percurso real (pior ponto)</caption>
            <thead className="text-left text-xs text-slate-500">
              <tr><th className="font-normal">Sistema</th><th className="font-normal">Origens</th><th className="font-normal">Maior percurso</th><th className="font-normal">Sem acesso</th></tr>
            </thead>
            <tbody>
              {Object.entries(region.coverage).map(([k, c]) => (
                <tr key={k} className="border-t border-slate-100">
                  <td>{c.label}</td>
                  <td className="tabular-nums">{c.sources}</td>
                  <td className="tabular-nums">{c.max_travel_m != null ? `${num(c.max_travel_m)} ± ${num(c.uncertainty_m)} m` : "—"}</td>
                  <td className="tabular-nums">{c.unreachable_m2 ? `${num(c.unreachable_m2)} m²` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {region.area_checks && region.area_checks.length > 0 && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-slate-700">
              Áreas declaradas × contorno ({region.area_checks.filter((c) => c.status === "DIVERGE").length} divergência(s))
            </summary>
            <ul className="mt-1 space-y-0.5">
              {region.area_checks.map((c, i) => (
                <li key={i} className={c.status === "DIVERGE" ? "text-red-800" : "text-slate-600"}>
                  {c.label}: declarada {num(c.declared_m2)} m², contorno {num(c.computed_m2)} m²
                  {c.status === "SEM_CONTORNO" ? " (sem contorno fechado)" : c.status === "DIVERGE" ? ` — diferença ${num(c.difference_m2)} m²` : " — confere"}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
      <div>
        {sorted.length === 0 && <p className="text-sm text-slate-500">Nenhum resultado com este filtro.</p>}
        <ul className="space-y-2">
          {sorted.map((r, i) => <ResultRow key={`${r.rule_id}-${r.subject_id}-${i}`} r={r} />)}
        </ul>
      </div>
    </div>
  );
}

function ResultRow({ r }: { r: RuleResult }) {
  const t = r.trace ?? {};
  const unit = t.unit ?? "";
  return (
    <li className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-slate-900">{r.title}</p>
          <p className="text-xs text-slate-500">{SUBJECT[r.subject_type] ?? r.subject_type}: {r.subject_label}</p>
        </div>
        <StatusBadge status={r.status} />
      </div>
      {t.measured !== undefined && (
        <p className="mt-1 text-slate-700">
          Medido <strong>{num(t.measured)}{t.uncertainty_abs ? ` ± ${num(t.uncertainty_abs)}` : ""} {unit}</strong>
          {t.required && <> · exigido {num(t.required)} {unit}</>}
          {r.status === "REVIEW_REQUIRED" && t.indicative && (
            <span className="text-slate-500"> · indicativo: {t.indicative === "PASS" ? "atende" : t.indicative === "FAIL" ? "não atende" : "inconclusivo (incerteza atravessa o limite)"}</span>
          )}
        </p>
      )}
      <p className="mt-1 text-xs text-slate-600">
        {REASONS[r.reason_code] ?? r.reason_code}
        {t.gate && ` — ${GATES[t.gate] ?? t.gate}`}
        {t.missing && t.missing.length > 0 && `: ${t.missing.join(", ")}`}
      </p>
      {r.citations.length > 0 && (
        <p className="mt-1 text-xs text-slate-500">
          {r.citations.map((c) => `${c.document} ${c.item}${c.page ? ` (p. ${c.page})` : ""}`).join("; ")}
        </p>
      )}
    </li>
  );
}

function Unrecognized({ data, classes, onMap }: {
  data: AnalysisJson; classes: { id: string }[]; onMap: (block: string) => void;
}) {
  const blocks = data.unrecognized_blocks ?? [];
  const outside = data.symbols_outside_regions?.length ?? 0;
  if (!blocks.length && !outside) return null;
  return (
    <div className="mt-6 grid gap-4 md:grid-cols-2">
      {blocks.length > 0 && (
        <div>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Blocos não reconhecidos (2 ou mais inserções)</h3>
          <ul className="space-y-1 text-sm">
            {blocks.map((b) => (
              <li key={`${b.block}-${b.layer}`} className="flex items-center gap-2">
                <code className="truncate rounded bg-slate-100 px-1">{b.block}</code>
                <span className="text-xs text-slate-500">{b.count}× · {b.layer}</span>
                {classes.length > 0 && (
                  <button className="ml-auto text-xs text-teal-800 underline" onClick={() => onMap(b.block)}>mapear</button>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-slate-500">“Mapear” leva o bloco para o item 5 do formulário; rode de novo a análise.</p>
        </div>
      )}
      {outside > 0 && (
        <p className="text-sm text-slate-600">
          {outside} símbolo(s) de segurança ficaram fora de todas as regiões analisadas — confira os recortes dos pavimentos.
        </p>
      )}
    </div>
  );
}
