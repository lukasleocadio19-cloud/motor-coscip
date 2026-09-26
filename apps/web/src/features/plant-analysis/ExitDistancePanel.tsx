import { useQuery } from "@tanstack/react-query";
import { api } from "@coscip/api-client";
import { ErrorState } from "@coscip/ui";
import type { PlantContext } from "./types";

interface ExitReference {
  status: string;
  message: string;
  limit_m: number | null;
  row?: string;
  column?: string;
  page?: number;
  by_floor_m?: Record<string, number>;
  measure?: "TRAVEL" | "DIRECT";
  base_limit_m?: number;
  reduction?: { factor: number; document: string; item: string };
  missing: string[];
  notes: { id: string; effect: string; text: string }[];
}

const missingLabels: Record<string, string> = {
  occupancy: "ocupação", construction_type: "tipo de edificação (α, β ou γ)",
  sprinklers_or_detection: "chuveiros ou detectores", multiple_exits: "número de saídas",
  layout_defined: "leiaute definido",
};

const columnLabels: Record<string, string> = {
  UNPROTECTED_SINGLE: "sem chuveiros/detectores, saída única",
  UNPROTECTED_MULTIPLE: "sem chuveiros/detectores, mais de uma saída",
  PROTECTED_SINGLE: "com chuveiros/detectores, saída única",
  PROTECTED_MULTIPLE: "com chuveiros/detectores, mais de uma saída",
};

/** Consulta ao Anexo C transcrito e conferido. Não grava: o limite só vale na análise. */
export function ExitDistancePanel({ packageId, context }: {
  packageId: string; context: Partial<PlantContext>;
}) {
  const query = useQuery({
    queryKey: ["exit-distance-query", packageId, context],
    queryFn: () => api<ExitReference>(`/rule-packages/${packageId}/exit-distance-query`, {
      method: "POST", json: context,
    }),
    enabled: Boolean(packageId),
  });
  const data = query.data;
  return <div className="my-3 rounded border border-slate-200 p-2 text-xs">
    <strong>Anexo C da NT 2-08 (rascunho)</strong>
    {query.error && <ErrorState error={query.error} />}
    {query.isFetching && <p role="status">Consultando a tabela…</p>}
    {data && <>
      {data.status === "FOUND" && data.limit_m != null && <p className="my-1 text-sm">
        Limite da tabela: <strong>{String(data.limit_m).replace(".", ",")} m</strong>
        {data.column && <> · {columnLabels[data.column] ?? data.column}</>}
        {data.page && <> · p. {data.page}</>}
      </p>}
      {data.reduction && <p className="my-1">
        Sem leiaute: {data.base_limit_m != null && <>tabela {data.base_limit_m} m, </>}reduzido em 30%
        ({data.reduction.document} {data.reduction.item}); distância medida em linha reta.
      </p>}
      {data.status === "DEPENDS_ON_FLOOR" && data.by_floor_m && <p className="my-1">
        Piso de descarga: {data.by_floor_m.DISCHARGE} m · demais pavimentos: {data.by_floor_m.OTHER} m.
      </p>}
      {data.missing.length > 0 && <p className="my-1">
        Falta informar: {data.missing.map((m) => missingLabels[m] ?? m).join(", ")}.
      </p>}
      {data.message && <p className="my-1">{data.message}</p>}
      {data.notes.length > 0 && <details><summary className="cursor-pointer">Observações do Anexo C</summary>
        {data.notes.map((n) => <p key={n.id} className="mt-2">{n.id}) {n.text}</p>)}
      </details>}
      <p className="mt-2">Se você informar o limite abaixo, ele prevalece sobre a tabela e a divergência
        fica registrada na análise.</p>
    </>}
  </div>;
}
