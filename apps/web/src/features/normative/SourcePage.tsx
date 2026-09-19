import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "@coscip/api-client";
import { Card, EmptyState, ErrorState, PageHeader } from "@coscip/ui";

import { Chip } from "./NormativePage";
import { NormText } from "./NormText";
import { SearchPanel } from "./SearchPanel";
import {
  coverageByDocument, fmtDate, shortHash,
  type PackageDetail, type PackageSummary, type SourceRow,
} from "./shared";

interface SourceDetail extends Omit<SourceRow, "items"> {
  effective: string | null;
  meta: Record<string, string>;
  summary: { pages: number; item_count: number };
  items: { id: string; kind: string; page: number | null; occurrences: number; head: string }[];
}

interface ItemText {
  document: string;
  item: string;
  occurrences: { page: number | null; kind: string; text: string }[];
}

const KIND_LABEL: Record<string, string> = {
  NUMBERED: "item", SECTION: "seção", TABLE: "tabela", ANNEX: "anexo", ARTICLE: "artigo",
};

export function SourcePage() {
  const { sourceId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const selected = params.get("item");
  const [filter, setFilter] = useState("");

  const source = useQuery({
    queryKey: ["normative-source", sourceId],
    queryFn: () => api<SourceDetail>(`/normative/sources/${sourceId}`),
  });
  const item = useQuery({
    queryKey: ["normative-item", sourceId, selected],
    queryFn: () => api<ItemText>(`/normative/sources/${sourceId}/item?item=${encodeURIComponent(selected!)}`),
    enabled: !!selected,
  });
  const packages = useQuery({
    queryKey: ["rule-packages"],
    queryFn: () => api<{ items: PackageSummary[] }>("/rule-packages"),
  });
  const latest = packages.data?.items.find((p) => p.verified);
  const pkg = useQuery({
    queryKey: ["rule-package", latest?.id],
    queryFn: () => api<PackageDetail>(`/rule-packages/${latest!.id}`),
    enabled: !!latest,
  });
  const s = source.data;
  const cov = useMemo(() => (s ? coverageByDocument(pkg.data).get(s.document) : undefined), [pkg.data, s]);
  const cited = useMemo(() => {
    const m = new Map<string, string[]>();
    for (const r of cov?.rules ?? []) m.set(r.citation.item, [...(m.get(r.citation.item) ?? []), "regra"]);
    for (const c of cov?.manual ?? []) m.set(c.item, [...(m.get(c.item) ?? []), "conferência"]);
    return m;
  }, [cov]);

  const f = filter.trim().toLowerCase();
  const items = (s?.items ?? []).filter((i) => !f || `${i.id} ${i.head}`.toLowerCase().includes(f));
  const pick = (id: string) => setParams({ item: id }, { replace: true });

  return (
    <>
      <PageHeader title={s ? s.document : "Documento normativo"}>
        <Link to="/base-normativa" className="rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-300">Voltar à base</Link>
        {s?.url && (
          <a href={s.url} target="_blank" rel="noreferrer noopener" className="rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-300">
            PDF oficial ↗
          </a>
        )}
      </PageHeader>
      {source.error && <ErrorState error={source.error} />}
      {s && (
        <>
          <p className="-mt-3 mb-4 text-slate-700">{s.title}</p>
          <div className="grid gap-4 lg:grid-cols-[20rem_minmax(0,1fr)]">
            <div className="flex min-w-0 flex-col gap-4">
              <Card title="Identificação">
                <dl className="grid grid-cols-[6rem_minmax(0,1fr)] gap-x-2 gap-y-1 break-words text-sm">
                  <dt className="text-slate-500">Edição</dt><dd>{s.edition}</dd>
                  <dt className="text-slate-500">Vigência</dt><dd>{s.effective ?? "—"}</dd>
                  <dt className="text-slate-500">Situação</dt><dd>{s.meta.status ?? "—"}</dd>
                  <dt className="text-slate-500">Captura</dt><dd>{s.collected_at ?? "—"}</dd>
                  <dt className="text-slate-500">Páginas</dt><dd>{s.meta.paginas_pdf ?? s.summary.pages}</dd>
                  <dt className="text-slate-500">Itens</dt><dd>{s.summary.item_count}</dd>
                  <dt className="text-slate-500">PDF</dt><dd><code className="text-xs" title={s.pdf_sha256 ?? ""}>{shortHash(s.pdf_sha256)}</code></dd>
                  <dt className="text-slate-500">Texto</dt><dd><code className="text-xs" title={s.text_sha256}>{shortHash(s.text_sha256)}</code></dd>
                  <dt className="text-slate-500">Ingestão</dt><dd>{fmtDate(s.created_at)}</dd>
                </dl>
                {!s.current && (
                  <p className="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-900">Existe ingestão mais recente deste documento; esta não é a vigente na base.</p>
                )}
              </Card>
              <Card title="No motor">
                {!cov && <p className="text-sm text-slate-600">Sem regra automática: documento disponível para consulta e citação.</p>}
                {cov && cov.rules.length > 0 && (
                  <>
                    <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Regras automáticas (rascunho)</h3>
                    <ul className="mb-3 space-y-1.5 text-sm">
                      {[...new Map(cov.rules.map((r) => [r.rule.rule_id, r.rule])).values()].map((rule) => (
                        <li key={rule.rule_id}>
                          <span className="text-slate-800">{rule.title}</span>
                          <span className="block text-xs text-slate-500">
                            {cov.rules.filter((r) => r.rule.rule_id === rule.rule_id).map(({ citation }, n) => (
                              <span key={citation.item}>
                                {n > 0 && " · "}
                                <button className="text-teal-800 underline" onClick={() => pick(citation.item)}>
                                  {citation.item}{citation.page ? ` (p. ${citation.page})` : ""}
                                </button>
                              </span>
                            ))}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {cov && cov.manual.length > 0 && (
                  <>
                    <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Conferência humana</h3>
                    <ul className="space-y-1 text-sm">
                      {cov.manual.map((c) => (
                        <li key={c.item}>
                          <button className="text-left text-teal-900 hover:underline" onClick={() => pick(c.item)}>{c.topic}</button>
                          <span className="block text-xs text-slate-500">{c.item} — {c.reason}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {cov?.dictionary && <p className="mt-2 text-xs text-slate-500">Base do dicionário de símbolos da planta.</p>}
              </Card>
              <Card title="Itens">
                <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filtrar (ex.: 5.2, Tabela)"
                  aria-label="Filtrar itens" className="mb-2 w-full rounded border border-slate-300 px-2 py-1 text-sm" />
                <ul className="max-h-[32rem] overflow-auto text-sm">
                  {items.map((i) => (
                    <li key={i.id}>
                      <button
                        onClick={() => pick(i.id)}
                        className={`w-full rounded px-2 py-1 text-left hover:bg-slate-50 ${selected === i.id ? "bg-teal-50 ring-1 ring-teal-600/30" : ""}`}
                      >
                        <span className="font-medium text-slate-800">{i.id}</span>
                        <span className="text-xs text-slate-500"> · {KIND_LABEL[i.kind] ?? i.kind}{i.page != null ? ` · p. ${i.page}` : ""}</span>
                        {cited.has(i.id) && <span className="ml-1"><Chip tone="teal">{cited.get(i.id)!.join(" + ")}</Chip></span>}
                        <span className="block truncate text-xs text-slate-500">{i.head}</span>
                      </button>
                    </li>
                  ))}
                  {items.length === 0 && <li className="p-2 text-slate-500">Nenhum item.</li>}
                </ul>
              </Card>
            </div>
            <div className="flex min-w-0 flex-col gap-4">
              <SearchPanel fixedDocument={s.document} />
              <Card title={selected ? `${s.document} — ${selected}` : "Texto do item"}>
                {!selected && <EmptyState>Escolha um item na lista, numa regra ou num resultado da busca.</EmptyState>}
                {item.error && <ErrorState error={item.error} />}
                {item.isLoading && <p className="text-sm text-slate-500">Carregando…</p>}
                {item.data?.occurrences.map((o, n) => (
                  <article key={n} className="mb-4">
                    {item.data.occurrences.length > 1 && (
                      <p className="mb-1 text-xs font-medium text-slate-500">
                        Ocorrência {n + 1} de {item.data.occurrences.length}{o.page != null ? ` · página ${o.page}` : ""}
                      </p>
                    )}
                    {item.data.occurrences.length === 1 && o.page != null && (
                      <p className="mb-1 text-xs font-medium text-slate-500">Página {o.page} do PDF</p>
                    )}
                    <div className="max-h-[40rem] overflow-auto rounded bg-slate-50 p-3">
                      <NormText text={o.text} />
                    </div>
                  </article>
                ))}
                {selected && (
                  <p className="text-xs text-slate-500">
                    Trecho do texto convertido (Markdown). Tabelas complexas e figuras: conferir no PDF oficial.
                  </p>
                )}
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  );
}
