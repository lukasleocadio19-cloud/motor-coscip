import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "@coscip/api-client";
import { Button, Card, EmptyState, ErrorState, PageHeader } from "@coscip/ui";

import {
  compareDocs, coverageByDocument, fmtDate, groupOf, GROUPS, shortHash,
  type DocCoverage, type PackageDetail, type PackageSummary, type SourceRow,
} from "./shared";
import { SearchPanel } from "./SearchPanel";

interface IngestResult {
  file: string;
  status: "INGESTED" | "ALREADY_PRESENT" | "REJECTED";
  document?: string;
  problem?: string;
}

const INGEST_LABEL: Record<IngestResult["status"], string> = {
  INGESTED: "ingerido",
  ALREADY_PRESENT: "já estava na base",
  REJECTED: "recusado",
};

export function NormativePage() {
  const qc = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [filter, setFilter] = useState("");
  const [ingest, setIngest] = useState<IngestResult[] | null>(null);
  const [showOld, setShowOld] = useState(false);

  const sources = useQuery({
    queryKey: ["normative-sources"],
    queryFn: () => api<{ items: SourceRow[] }>("/normative/sources"),
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
  const coverage = useMemo(() => coverageByDocument(pkg.data), [pkg.data]);

  const upload = useMutation({
    mutationFn: async (files: FileList) => {
      const form = new FormData();
      for (const f of Array.from(files)) form.append("files", f);
      return api<{ items: IngestResult[] }>("/normative/sources", { method: "POST", body: form });
    },
    onSuccess: (r) => {
      setIngest(r.items);
      void qc.invalidateQueries({ queryKey: ["normative-sources"] });
    },
  });
  const importPkg = useMutation({
    mutationFn: () => api<{ id: string; status: string }>("/rule-packages/import", { method: "POST" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["rule-packages"] }),
  });
  const importFailures =
    importPkg.error instanceof ApiError
      ? ((importPkg.error.problem as unknown as { details?: { failures?: string[] } }).details?.failures ?? [])
      : [];

  const current = (sources.data?.items ?? []).filter((s) => s.current);
  const superseded = (sources.data?.items ?? []).filter((s) => !s.current);
  const q = filter.trim().toLowerCase();
  const shown = current
    .filter((s) => !q || `${s.document} ${s.title}`.toLowerCase().includes(q))
    .sort((a, b) => compareDocs(a.document, b.document));
  const automated = current.filter((s) => (coverage.get(s.document)?.rules.length ?? 0) > 0).length;

  return (
    <>
      <PageHeader title="Base normativa">
        <input
          ref={fileInput}
          type="file"
          accept=".md,.markdown,.txt"
          multiple
          className="hidden"
          onChange={(e) => e.target.files?.length && upload.mutate(e.target.files)}
        />
        <Button variant="ghost" onClick={() => fileInput.current?.click()} disabled={upload.isPending}>
          {upload.isPending ? "Enviando…" : "Enviar textos (.md)"}
        </Button>
        <Button onClick={() => importPkg.mutate()} disabled={importPkg.isPending || current.length === 0}>
          {importPkg.isPending ? "Conferindo citações…" : "Importar pacote de regras"}
        </Button>
      </PageHeader>

      <p className="mb-5 max-w-3xl text-sm text-slate-600">
        Textos integrais das Notas Técnicas e do COSCIP, guardados com SHA-256. Cada regra automática só
        entra em um pacote se todas as citações dela forem encontradas no texto vigente (documento, item e
        termos). As regras estão em <strong>rascunho</strong>: nenhum resultado tem valor normativo até a
        homologação por responsável técnico.
      </p>

      <div className="mb-4 grid gap-4 md:grid-cols-4">
        <Stat label="Documentos vigentes" value={sources.isLoading ? "…" : String(current.length)}
          note={superseded.length ? `${superseded.length} ingestão(ões) anterior(es)` : "sem versões anteriores"} />
        <Stat label="Com regra automática" value={pkg.data ? String(automated) : "—"}
          note="demais: consulta e conferência humana" />
        <Stat label="Regras no pacote" value={latest ? String(latest.rules) : "—"}
          note={latest ? `${latest.state === "DRAFT" ? "rascunho" : latest.state} · ${fmtDate(latest.created_at)}` : "nenhum pacote importado"} />
        <Stat label="Itens de conferência humana" value={pkg.data ? String(pkg.data.manifest.coverage.length) : "—"}
          note="com motivo e citação" />
      </div>

      {upload.error && <ErrorState error={upload.error} />}
      {ingest && (
        <Card title="Resultado do envio">
          <ul className="max-h-48 space-y-0.5 overflow-auto text-sm">
            {ingest.map((r) => (
              <li key={r.file} className={r.status === "REJECTED" ? "text-red-800" : "text-slate-700"}>
                <span className="font-medium">{r.document ?? r.file}</span> — {INGEST_LABEL[r.status]}
                {r.problem && <span>: {r.problem}</span>}
              </li>
            ))}
          </ul>
          <button className="mt-2 text-xs text-slate-500 underline" onClick={() => setIngest(null)}>fechar</button>
        </Card>
      )}
      {importPkg.data && (
        <p role="status" className="mb-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          {importPkg.data.status === "IMPORTED" ? "Pacote importado: todas as citações conferem." : "O pacote já estava importado com estes textos."}
        </p>
      )}
      {importPkg.error && (
        <div className="mb-4">
          <ErrorState error={importPkg.error} />
          {importFailures.length > 0 && (
            <ul className="mt-2 list-disc pl-6 text-sm text-red-800">
              {importFailures.map((f) => <li key={f}>{f}</li>)}
            </ul>
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-w-0 flex-col gap-4">
          <SearchPanel documents={current.map((s) => s.document).sort(compareDocs)} />
          <Card title="Documentos">
            <label className="mb-3 block text-sm">
              <span className="sr-only">Filtrar documentos</span>
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filtrar por número ou título (ex.: 2-08, saídas)"
                className="w-full rounded border border-slate-300 px-3 py-1.5"
              />
            </label>
            {sources.error && <ErrorState error={sources.error} />}
            {sources.data && current.length === 0 && (
              <EmptyState>
                Nenhum texto na base. Envie os arquivos .md das NTs (com front matter) pelo botão acima ou
                pelo comando <code>coscip_api.cli normative-import-sources &lt;pasta&gt;</code>.
              </EmptyState>
            )}
            {GROUPS.map((g) => {
              const docs = shown.filter((s) => groupOf(s.document) === g.key);
              if (!docs.length) return null;
              return (
                <section key={g.key} className="mb-4">
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {g.label} <span className="font-normal">({docs.length})</span>
                  </h3>
                  <ul className="divide-y divide-slate-100">
                    {docs.map((s) => (
                      <DocRow key={s.id} source={s} cov={coverage.get(s.document)} />
                    ))}
                  </ul>
                </section>
              );
            })}
            {q && shown.length === 0 && <EmptyState>Nenhum documento com “{filter}”.</EmptyState>}
            {superseded.length > 0 && (
              <div className="mt-2 text-sm">
                <button className="text-slate-600 underline" onClick={() => setShowOld(!showOld)}>
                  {showOld ? "Ocultar" : "Mostrar"} ingestões anteriores ({superseded.length})
                </button>
                {showOld && (
                  <ul className="mt-2 space-y-1 text-slate-600">
                    {superseded.map((s) => (
                      <li key={s.id}>
                        {s.document} · {s.edition} · texto <code className="text-xs">{shortHash(s.text_sha256)}</code> · {fmtDate(s.created_at)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Card>
        </div>

        <div className="flex min-w-0 flex-col gap-4">
          <PackageCard pkg={pkg.data} loading={pkg.isLoading || packages.isLoading} others={packages.data?.items ?? []} />
        </div>
      </div>
    </>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      <p className="text-xs text-slate-500">{note}</p>
    </div>
  );
}

function DocRow({ source: s, cov }: { source: SourceRow; cov?: DocCoverage }) {
  const rules = new Set(cov?.rules.map((r) => r.rule.rule_id)).size;
  const manual = cov?.manual.length ?? 0;
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
      <Link to={`/base-normativa/${s.id}`} className="min-w-0 flex-1 hover:underline">
        <span className="font-semibold text-teal-900">{s.document}</span>{" "}
        <span className="text-slate-700">{s.title.replace(/^(NT \d-\d{2}( - Parte \d)?|Decreto[^-]*) - /, "")}</span>
        <span className="block text-xs text-slate-500">{s.edition} · {s.items ?? "?"} itens indexados</span>
      </Link>
      <span className="flex flex-wrap gap-1">
        {rules > 0 && <Chip tone="teal">{rules} regra{rules > 1 ? "s" : ""} automática{rules > 1 ? "s" : ""}</Chip>}
        {manual > 0 && <Chip tone="amber">{manual} conferência{manual > 1 ? "s" : ""} humana{manual > 1 ? "s" : ""}</Chip>}
        {cov?.dictionary && <Chip tone="slate">símbolos</Chip>}
        {!rules && !manual && !cov?.dictionary && <Chip tone="slate">consulta</Chip>}
      </span>
    </li>
  );
}

export function Chip({ tone, children }: { tone: "teal" | "amber" | "slate" | "red"; children: React.ReactNode }) {
  const cls = {
    teal: "bg-teal-50 text-teal-900 ring-teal-600/30",
    amber: "bg-amber-50 text-amber-900 ring-amber-600/30",
    slate: "bg-slate-50 text-slate-600 ring-slate-400/30",
    red: "bg-red-50 text-red-800 ring-red-600/30",
  }[tone];
  return <span className={`inline-flex rounded px-2 py-0.5 text-xs ring-1 ${cls}`}>{children}</span>;
}

function PackageCard({ pkg, loading, others }: { pkg?: PackageDetail; loading: boolean; others: PackageSummary[] }) {
  if (loading) return <Card title="Pacote de regras"><p className="text-sm text-slate-500">Carregando…</p></Card>;
  if (!pkg) {
    return (
      <Card title="Pacote de regras">
        <EmptyState>
          Nenhum pacote verificado. Depois de enviar os textos, use “Importar pacote de regras”: o motor
          confere cada citação antes de aceitar.
        </EmptyState>
      </Card>
    );
  }
  return (
    <Card title="Pacote de regras vigente">
      <p className="text-sm font-medium text-slate-800">{pkg.name}</p>
      <p className="mt-1 text-xs text-slate-500">
        {pkg.package?.id} v{pkg.package?.version} · {pkg.jurisdiction} · importado {fmtDate(pkg.created_at)}
      </p>
      <p className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-900 ring-1 ring-amber-600/30">
        Rascunho, sem homologação: resultados apenas indicativos.
      </p>
      <p className="mt-2 text-xs text-slate-500">
        Pacote <code>{shortHash(pkg.content_sha256)}</code> · textos <code>{shortHash(pkg.manifest.sources_sha256)}</code>
      </p>
      <h3 className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Regras</h3>
      <ul className="space-y-2 text-sm">
        {pkg.manifest.rules.map((r) => (
          <li key={r.rule_id}>
            <p className="text-slate-800">{r.title}</p>
            <p className="text-xs text-slate-500">
              {r.rule_id} v{r.version} ·{" "}
              {r.citations.map((c) => `${c.document} ${c.item}${c.page ? ` (p. ${c.page})` : ""}`).join("; ")}
            </p>
          </li>
        ))}
      </ul>
      <h3 className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Conferência humana</h3>
      <ul className="space-y-2 text-sm">
        {pkg.manifest.coverage.map((c) => (
          <li key={`${c.document}-${c.item}`}>
            <p className="text-slate-800">{c.topic}</p>
            <p className="text-xs text-slate-500">{c.document} {c.item} — {c.reason}</p>
          </li>
        ))}
      </ul>
      {others.length > 1 && (
        <p className="mt-4 text-xs text-slate-500">{others.length - 1} pacote(s) anterior(es) mantido(s) para reprodutibilidade das análises antigas.</p>
      )}
    </Card>
  );
}
