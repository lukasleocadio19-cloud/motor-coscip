import { useQuery } from "@tanstack/react-query";
import { api } from "@coscip/api-client";
import { ErrorState } from "@coscip/ui";
import type { PlantContext } from "./types";

interface Reference {
  status: string;
  message: string;
  column?: string;
  source: { document: string; item: string; page: number } | null;
  measures: { id: string; label: string; cell: string; status: string }[];
  notes: string[];
  conflicts?: string[];
}

const labels: Record<string, string> = {
  REQUIRED: "Exigido na tabela", CONDITIONAL: "Conferir condição da nota",
  NOT_MARKED: "Não assinalado nesta tabela",
};

export function RequirementsPanel({ packageId, context }: {
  packageId: string; context: Partial<PlantContext>;
}) {
  const query = useQuery({
    queryKey: ["requirements-query", packageId, context],
    queryFn: () => api<Reference>(`/rule-packages/${packageId}/requirements-query`, {
      method: "POST", json: context,
    }),
    enabled: Boolean(packageId),
  });
  return <div className="my-3 rounded border border-slate-200 p-2 text-xs">
    <strong>Referência do Anexo III (rascunho)</strong>
    {query.error && <ErrorState error={query.error} />}
    {query.isFetching && <p role="status">Consultando o pacote selecionado…</p>}
    {query.data && <>
      <p className="my-1">{query.data.message}</p>
      {query.data.source && <p>{query.data.source.item} · PDF p. {query.data.source.page}</p>}
      {query.data.column && <p>Coluna: {query.data.column}</p>}
      {query.data.measures.length > 0 && <table className="my-2 w-full text-left"><tbody>
        {query.data.measures.map((m) => <tr key={m.id} className="border-t border-slate-100">
          <th className="py-1 font-normal">{m.label}</th>
          <td className="pl-2">{m.cell} · {labels[m.status] ?? m.status}</td>
        </tr>)}
      </tbody></table>}
      {query.data.conflicts?.map((warning) => <p key={warning} role="alert"
        className="my-2 rounded bg-amber-50 p-2 text-amber-900">{warning}</p>)}
      {query.data.notes.length > 0 && <details><summary className="cursor-pointer">Notas da tabela</summary>
        {query.data.notes.map((n, i) => <p key={i} className="mt-2">{n}</p>)}
      </details>}
      <p className="mt-2">Na Tabela 2, hidrantes e alarme não têm linha própria. Confirme abaixo os sistemas
        exigidos no processo; a consulta não altera essas escolhas.</p>
    </>}
  </div>;
}
