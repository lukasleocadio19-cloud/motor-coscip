import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "@coscip/api-client";
import { Card, EmptyState, ErrorState, PageHeader } from "@coscip/ui";

interface Diag {
  drawing_id: string;
  file: string;
  cad_version: string | null;
  diagnostics: {
    insunits_name: string;
    units_declared: boolean;
    layers: string[];
    xrefs: string[];
    entity_counts: Record<string, number>;
    unsupported_counts: Record<string, number>;
    quality_counts: Record<string, number>;
    expanded_count: number;
    warnings: string[];
    layout_entity_counts?: Record<string, number>;
    unit_suggestion?: {
      unit: string | null;
      strength: string;
      note: string;
      samples: number[];
    } | null;
  };
}

const UNIT_NAMES: Record<string, string> = { m: "metros", cm: "centímetros", mm: "milímetros" };

export function DiagnosticsPage() {
  const { revisionId = "" } = useParams();
  const q = useQuery({
    queryKey: ["diagnostics", revisionId],
    queryFn: () => api<{ items: Diag[] }>(`/revisions/${revisionId}/diagnostics`),
  });

  return (
    <>
      <PageHeader title="Diagnóstico de importação" />
      {q.error && <ErrorState error={q.error} />}
      {q.data?.items.length === 0 && <EmptyState>Nenhum desenho importado ainda.</EmptyState>}
      <div className="grid gap-4">
        {q.data?.items.map((d) => (
          <Card key={d.drawing_id} title={`${d.file} · ${d.cad_version ?? ""}`}>
            {d.diagnostics.warnings.map((w) => (
              <p key={w} role="alert" className="mb-2 rounded bg-amber-50 p-2 text-sm text-amber-900">⚠ {w}</p>
            ))}
            <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm md:grid-cols-4">
              <dt className="text-slate-500">Unidade declarada</dt>
              <dd>{d.diagnostics.insunits_name}{!d.diagnostics.units_declared && " (confirmar)"}</dd>
              <dt className="text-slate-500">Layers</dt><dd>{d.diagnostics.layers.length}</dd>
              <dt className="text-slate-500">XRefs</dt><dd>{d.diagnostics.xrefs.length}</dd>
              <dt className="text-slate-500">Entidades expandidas</dt><dd>{d.diagnostics.expanded_count}</dd>
            </dl>
            {d.diagnostics.unit_suggestion && (
              <div className="mt-4 rounded border border-slate-200 bg-slate-50 p-3 text-sm">
                <p className="font-medium">
                  Unidade sugerida pelas cotas:{" "}
                  {d.diagnostics.unit_suggestion.unit
                    ? `${UNIT_NAMES[d.diagnostics.unit_suggestion.unit]} (indício ${d.diagnostics.unit_suggestion.strength})`
                    : "sem indício"}
                </p>
                <p className="text-xs text-slate-600">{d.diagnostics.unit_suggestion.note}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Sugestão, não decisão: confirme com uma medida conhecida antes de qualquer cálculo.
                </p>
              </div>
            )}
            {d.diagnostics.layout_entity_counts && (
              <>
                <h3 className="mt-4 text-xs font-semibold uppercase text-slate-500">Entidades por espaço</h3>
                <ul className="text-sm">
                  {Object.entries(d.diagnostics.layout_entity_counts).map(([k, v]) => (
                    <li key={k}>{k === "Model" ? "Model (analisado)" : `Prancha ${k}`}: {v}</li>
                  ))}
                </ul>
              </>
            )}
            <h3 className="mt-4 text-xs font-semibold uppercase text-slate-500">Matriz de suporte</h3>
            <ul className="text-sm">
              {Object.entries(d.diagnostics.quality_counts).map(([k, v]) => <li key={k}>{k}: {v}</li>)}
            </ul>
            {Object.keys(d.diagnostics.unsupported_counts).length > 0 && (
              <>
                <h3 className="mt-4 text-xs font-semibold uppercase text-slate-500">Não suportadas (inventariadas, não descartadas)</h3>
                <ul className="text-sm">
                  {Object.entries(d.diagnostics.unsupported_counts).map(([k, v]) => <li key={k}>{k}: {v}</li>)}
                </ul>
              </>
            )}
          </Card>
        ))}
      </div>
    </>
  );
}
