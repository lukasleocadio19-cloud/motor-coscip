import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@coscip/api-client";
import { Card, EmptyState, ErrorState } from "@coscip/ui";

interface Hit {
  source_id: string;
  document: string;
  title: string;
  item: string;
  page: number | null;
  excerpt: string;
}

/** Busca por termos em todas as fontes vigentes (todos os termos no mesmo item). */
export function SearchPanel({ documents, fixedDocument }: { documents?: string[]; fixedDocument?: string }) {
  const [text, setText] = useState("");
  const [doc, setDoc] = useState(fixedDocument ?? "");
  const [query, setQuery] = useState<{ q: string; doc: string } | null>(null);

  const hits = useQuery({
    queryKey: ["normative-search", query],
    queryFn: () => {
      const p = new URLSearchParams({ q: query!.q });
      if (query!.doc) p.set("document", query!.doc);
      return api<{ items: Hit[]; truncated: boolean }>(`/normative/search?${p}`);
    },
    enabled: !!query,
  });

  return (
    <Card title={fixedDocument ? `Buscar na ${fixedDocument}` : "Buscar nas normas"}>
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim().length >= 2) setQuery({ q: text.trim(), doc });
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Termos, ex.: distância máxima percorrida"
          aria-label="Termos da busca"
          className="min-w-[12rem] flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm"
        />
        {!fixedDocument && documents && (
          <select value={doc} onChange={(e) => setDoc(e.target.value)} aria-label="Documento"
            className="max-w-[9rem] rounded border border-slate-300 px-2 py-1.5 text-sm">
            <option value="">Todas</option>
            {documents.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        )}
        <button className="rounded-md bg-teal-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-800">Buscar</button>
      </form>
      <p className="mt-1 text-xs text-slate-500">Sem diferença de acentos ou maiúsculas; palavras longas valem pelo radical (percorrer ~ percorrida); todos os termos no mesmo item.</p>
      {hits.error && <ErrorState error={hits.error} />}
      {hits.isFetching && <p className="mt-3 text-sm text-slate-500">Buscando…</p>}
      {hits.data && !hits.isFetching && (
        <div className="mt-3">
          {hits.data.items.length === 0 && <EmptyState>Nenhum item com todos esses termos.</EmptyState>}
          <ul className="max-h-[28rem] divide-y divide-slate-100 overflow-auto">
            {hits.data.items.map((h) => (
              <li key={`${h.source_id}-${h.item}`} className="py-2 text-sm">
                <Link
                  to={`/base-normativa/${h.source_id}?item=${encodeURIComponent(h.item)}`}
                  className="font-medium text-teal-900 hover:underline"
                >
                  {h.document} · {h.item}
                </Link>
                {h.page != null && <span className="text-xs text-slate-500"> · p. {h.page}</span>}
                <p className="mt-0.5 text-slate-600">{h.excerpt}</p>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-500">
            {hits.data.items.length} resultado(s){hits.data.truncated ? " — lista cortada; refine os termos" : ""}.
          </p>
        </div>
      )}
    </Card>
  );
}
