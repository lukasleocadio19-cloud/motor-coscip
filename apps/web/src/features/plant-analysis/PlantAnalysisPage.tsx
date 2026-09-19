import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "@coscip/api-client";
import { Button, Card, EmptyState, ErrorState, ExecutionBadge, PageHeader } from "@coscip/ui";

import { AnalysisResult } from "./AnalysisResult";
import {
  type Division, type DrawingInfo, type PlantAnalysis, type PlantContext, type PlantOptions, type Risk,
  STATUS_ORDER, TERMINAL,
} from "./types";

type Tri = "" | "sim" | "nao";
const triValue = (t: Tri) => (t === "" ? null : t === "sim");
const toTri = (v: boolean | null | undefined): Tri => (v == null ? "" : v ? "sim" : "nao");

const RISKS: { v: Risk | ""; label: string }[] = [
  { v: "", label: "Não informado" },
  { v: "PEQUENO", label: "Pequeno" },
  { v: "MEDIO", label: "Médio" },
  { v: "GRANDE", label: "Grande" },
];

const STATUS_SHORT: Record<string, string> = {
  FAIL: "pendência", REVIEW_REQUIRED: "revisão", MISSING_DATA: "dado ausente",
  PASS: "conforme", NOT_APPLICABLE: "não se aplica",
};

export function PlantAnalysisPage() {
  const { drawingId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const selected = params.get("analise");
  const qc = useQueryClient();

  const drawing = useQuery({
    queryKey: ["drawing", drawingId],
    queryFn: () => api<DrawingInfo>(`/drawings/${drawingId}`),
  });
  const options = useQuery({
    queryKey: ["plant-options", drawingId],
    queryFn: () => api<PlantOptions>(`/drawings/${drawingId}/plant-analysis-options`),
  });
  const history = useQuery({
    queryKey: ["plant-analyses", drawingId],
    queryFn: () => api<{ items: PlantAnalysis[] }>(`/drawings/${drawingId}/plant-analyses`),
    refetchInterval: (q) => (q.state.data?.items.some((a) => !TERMINAL.has(a.state)) ? 2000 : false),
  });

  // --- formulário --------------------------------------------------------------------
  const [packageId, setPackageId] = useState("");
  const [risk, setRisk] = useState<Risk | "">("");
  const [occupancy, setOccupancy] = useState("");
  const [riskBasis, setRiskBasis] = useState<string | null>(null);
  const [unifamiliar, setUnifamiliar] = useState(false);
  const [hydrants, setHydrants] = useState<Tri>("");
  const [alarm, setAlarm] = useState<Tri>("");
  const [lighting, setLighting] = useState<Tri>("");
  const [exitMax, setExitMax] = useState("");
  const [exitsConfirmed, setExitsConfirmed] = useState(false);
  const [useFloors, setUseFloors] = useState(true);
  const [floorIds, setFloorIds] = useState<Set<string> | null>(null);
  const [wallMode, setWallMode] = useState<"auto" | "manual">("auto");
  const [walls, setWalls] = useState<Set<string>>(new Set());
  const [layerFilter, setLayerFilter] = useState("");
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [newBlock, setNewBlock] = useState("");
  const [prefilled, setPrefilled] = useState(false);

  const opts = options.data;
  useEffect(() => {
    if (opts && !packageId && opts.packages[0]) setPackageId(opts.packages[0].id);
    if (opts && walls.size === 0) setWalls(new Set(opts.layers.filter((l) => l.suggested_obstacle).map((l) => l.name)));
  }, [opts]);

  // Reaproveita o enquadramento da última análise desta planta.
  useEffect(() => {
    const last = history.data?.items[0]?.context;
    if (prefilled || !history.data) return;
    setPrefilled(true);
    if (!last) return;
    setRisk(last.risk_class ?? "");
    setOccupancy(last.occupancy ?? "");
    setRiskBasis(last.risk_basis ?? null);
    setUnifamiliar(last.unifamiliar);
    setHydrants(toTri(last.requires_hydrants));
    setAlarm(toTri(last.requires_alarm));
    setLighting(toTri(last.requires_lighting));
    setExitMax(last.exit_max_distance_m != null ? String(last.exit_max_distance_m).replace(".", ",") : "");
    setExitsConfirmed(last.exits_confirmed);
  }, [history.data, prefilled]);

  const floors = drawing.data?.floors ?? opts?.floors ?? [];
  const cls = opts?.classification ?? null;
  const divisions = cls?.divisions ?? [];
  const division = divisions.find((d) => d.id === occupancy);
  const groups = useMemo(() => {
    const m = new Map<string, Division[]>();
    for (const d of divisions) m.set(d.group, [...(m.get(d.group) ?? []), d]);
    return [...m.entries()];
  }, [divisions]);
  const pickDivision = (id: string) => {
    setOccupancy(id);
    const d = divisions.find((x) => x.id === id);
    if (d && cls) {
      setRisk(cls.risk_to_rules[d.risk]);
      setRiskBasis(`NT 1-04, Anexo B (p. ${d.page}): ${d.id} ${d.description.slice(0, 60)} → ${d.risk}`
        + (d.merged_from ? ` (célula mesclada com ${d.merged_from})` : ""));
    }
  };
  const chosenFloors = floorIds ?? new Set(floors.map((f) => f.id));
  const exitMaxNum = exitMax.trim() ? Number(exitMax.replace(",", ".")) : null;
  const exitInvalid = exitMaxNum !== null && !(exitMaxNum > 0 && exitMaxNum <= 300);

  const create = useMutation({
    mutationFn: () => {
      const context: PlantContext = {
        risk_class: risk || null,
        unifamiliar,
        occupancy: occupancy.trim() || null,
        risk_basis: risk ? riskBasis ?? "informada pelo analista" : null,
        requires_hydrants: triValue(hydrants),
        requires_alarm: triValue(alarm),
        requires_lighting: triValue(lighting),
        exit_max_distance_m: exitMaxNum,
        exits_confirmed: exitsConfirmed,
      };
      return api<{ analysis_id: string }>(`/drawings/${drawingId}/plant-analyses`, {
        method: "POST",
        idempotencyKey: crypto.randomUUID(),
        json: {
          rule_package_id: packageId,
          context,
          use_floors: useFloors && floors.length > 0,
          floor_ids: useFloors && floors.length > 0 ? [...chosenFloors] : null,
          obstacle_layers: wallMode === "manual" ? [...walls] : null,
          symbol_overrides: Object.fromEntries(Object.entries(overrides).filter(([, v]) => v)),
        },
      });
    },
    onSuccess: (r) => {
      setParams({ analise: r.analysis_id });
      void qc.invalidateQueries({ queryKey: ["plant-analyses", drawingId] });
    },
  });

  const unitOk = drawing.data?.unit.confirmed;
  const noPackage = opts && opts.packages.length === 0;
  const blocked = !unitOk || !packageId || exitInvalid || (useFloors && floors.length > 0 && chosenFloors.size === 0);
  const layers = useMemo(() => {
    const f = layerFilter.trim().toLowerCase();
    return (opts?.layers ?? []).filter((l) => !f || l.name.toLowerCase().includes(f));
  }, [opts, layerFilter]);

  const current = selected ?? history.data?.items[0]?.id ?? null;

  return (
    <>
      <PageHeader title="Análise da planta">
        <Link to={`/desenhos/${drawingId}`} className="rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-300">Planta e recortes</Link>
        <Link to="/base-normativa" className="rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-300">Base normativa</Link>
      </PageHeader>
      <p className="-mt-3 mb-4 text-sm text-slate-600">
        {drawing.data?.file ?? "…"}
        {drawing.data?.unit.confirmed && <> · unidade confirmada: {drawing.data.unit.unit}</>}
      </p>
      {drawing.error && <ErrorState error={drawing.error} />}
      {options.error && <ErrorState error={options.error} />}

      {drawing.data && !unitOk && (
        <p role="alert" className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          A unidade do desenho ainda não foi confirmada. Confirme com uma medida conhecida na{" "}
          <Link className="underline" to={`/desenhos/${drawingId}`}>tela da planta</Link> antes de analisar.
        </p>
      )}
      {noPackage && (
        <p role="alert" className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          Nenhum pacote de regras verificado. Envie os textos das NTs e importe o pacote na{" "}
          <Link className="underline" to="/base-normativa">Base normativa</Link>.
        </p>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_20rem]">
        <form
          className="grid content-start gap-4 md:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!blocked) create.mutate();
          }}
        >
          <Card title="1. Enquadramento (dados do processo)">
            <fieldset className="mb-3">
              <legend className="mb-1 text-sm text-slate-700">Classe de risco (NT 2-01, Tabela 3)</legend>
              <div className="flex flex-wrap gap-3 text-sm">
                {RISKS.map((r) => (
                  <label key={r.v} className="flex items-center gap-1">
                    <input type="radio" name="risk" checked={risk === r.v}
                      onChange={() => { setRisk(r.v); setRiskBasis(null); }} />
                    {r.label}
                  </label>
                ))}
              </div>
              {!risk && <p className="mt-1 text-xs text-amber-800">Sem a classe, distância e área por extintor ficam como “dado ausente”.</p>}
              {risk && <p className="mt-1 text-xs text-slate-500">Origem: {riskBasis ?? "informada pelo analista"}</p>}
            </fieldset>
            <label className="mb-2 block text-sm">
              Ocupação / divisão (Decreto 42/2018, Anexo II)
              {divisions.length > 0 ? (
                <select value={occupancy} onChange={(e) => pickDivision(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1">
                  <option value="">não informada</option>
                  {groups.map(([g, ds]) => (
                    <optgroup key={g} label={g}>
                      {ds.map((d) => <option key={d.id} value={d.id}>{d.id} — {d.description.slice(0, 70)}</option>)}
                    </optgroup>
                  ))}
                  {occupancy && !divisions.some((d) => d.id === occupancy) && <option value={occupancy}>{occupancy}</option>}
                </select>
              ) : (
                <input value={occupancy} onChange={(e) => setOccupancy(e.target.value)} maxLength={20}
                  placeholder="ex.: C-2" className="mt-1 w-full rounded border border-slate-300 px-2 py-1" />
              )}
            </label>
            {division && (
              <p className="mb-2 rounded bg-teal-50 px-2 py-1 text-xs text-teal-900 ring-1 ring-teal-600/20">
                NT 1-04, Anexo B (p. {division.page}): risco <strong>{division.risk}</strong>
                {division.merged_from && <> (célula mesclada com {division.merged_from})</>} → coluna{" "}
                <strong>{RISKS.find((r) => r.v === cls?.risk_to_rules[division.risk])?.label}</strong> da NT 2-01, Tabela 3.
              </p>
            )}
            {cls && cls.notes.length > 1 && (
              <details className="mb-2 text-xs text-slate-600">
                <summary className="cursor-pointer">Exceções da NT 1-04 que o analista confere</summary>
                <p className="mt-1">{cls.notes[1]}</p>
              </details>
            )}
            <label className="mb-3 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={unifamiliar} onChange={(e) => setUnifamiliar(e.target.checked)} />
              Residência unifamiliar
            </label>
            <p className="mb-1 text-sm text-slate-700">Sistemas exigidos (Anexo III do decreto)</p>
            <div className="grid gap-1 text-sm">
              <TriSelect label="Hidrantes" value={hydrants} onChange={setHydrants} />
              <TriSelect label="Alarme" value={alarm} onChange={setAlarm} />
              <TriSelect label="Iluminação" value={lighting} onChange={setLighting} />
            </div>
          </Card>

          <Card title="2. Saídas (NT 2-08)">
            <label className="mb-2 block text-sm">
              Distância máxima até a saída, em metros
              <input value={exitMax} onChange={(e) => setExitMax(e.target.value)} inputMode="decimal"
                placeholder="da tabela do Anexo C" aria-invalid={exitInvalid}
                className={`mt-1 w-full rounded border px-2 py-1 ${exitInvalid ? "border-red-500" : "border-slate-300"}`} />
            </label>
            {exitInvalid && <p className="mb-2 text-xs text-red-700">Informe um valor entre 0 e 300 m.</p>}
            <p className="mb-3 text-xs text-slate-500">
              O Anexo C da NT 2-08 está como imagem na base: o analista informa o limite aplicável à ocupação.
            </p>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={exitsConfirmed} onChange={(e) => setExitsConfirmed(e.target.checked)} />
              Conferi que as saídas marcadas na planta são as saídas de emergência
            </label>
          </Card>

          <Card title="3. Pavimentos">
            {floors.length === 0 ? (
              <p className="text-sm text-amber-900">
                Nenhum pavimento recortado. O motor agrupa as regiões sozinho e <strong>todo resultado fica em revisão</strong>.
                Recorte os pavimentos na <Link className="underline" to={`/desenhos/${drawingId}`}>tela da planta</Link>.
              </p>
            ) : (
              <>
                <label className="mb-2 flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={useFloors} onChange={(e) => setUseFloors(e.target.checked)} />
                  Usar os recortes feitos na planta
                </label>
                <ul className="space-y-1 text-sm">
                  {floors.map((f) => (
                    <li key={f.id}>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          disabled={!useFloors}
                          checked={chosenFloors.has(f.id)}
                          onChange={(e) => {
                            const next = new Set(chosenFloors);
                            if (e.target.checked) next.add(f.id); else next.delete(f.id);
                            setFloorIds(next);
                          }}
                        />
                        {f.name}
                      </label>
                    </li>
                  ))}
                </ul>
                {!useFloors && <p className="mt-2 text-xs text-amber-800">Sem recortes, as regiões são automáticas e tudo vai para revisão.</p>}
              </>
            )}
          </Card>

          <Card title="4. Paredes (obstáculos do percurso)">
            <div className="mb-2 flex gap-4 text-sm">
              <label className="flex items-center gap-1">
                <input type="radio" checked={wallMode === "auto"} onChange={() => setWallMode("auto")} /> Reconhecer pelo nome da camada
              </label>
              <label className="flex items-center gap-1">
                <input type="radio" checked={wallMode === "manual"} onChange={() => setWallMode("manual")} /> Escolher camadas
              </label>
            </div>
            {wallMode === "auto" ? (
              <p className="text-xs text-slate-500">
                Sugeridas: {(opts?.layers ?? []).filter((l) => l.suggested_obstacle).map((l) => l.name).join(", ") || "nenhuma — o percurso vira linha reta e fica em revisão"}
              </p>
            ) : (
              <>
                <input value={layerFilter} onChange={(e) => setLayerFilter(e.target.value)} placeholder="Filtrar camadas"
                  aria-label="Filtrar camadas" className="mb-2 w-full rounded border border-slate-300 px-2 py-1 text-sm" />
                <ul className="max-h-48 overflow-auto text-sm">
                  {layers.map((l) => (
                    <li key={l.name}>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={walls.has(l.name)}
                          onChange={(e) => {
                            const next = new Set(walls);
                            if (e.target.checked) next.add(l.name); else next.delete(l.name);
                            setWalls(next);
                          }}
                        />
                        <span className="truncate">{l.name}</span>
                        <span className="ml-auto text-xs text-slate-400">{l.segments}</span>
                      </label>
                    </li>
                  ))}
                </ul>
                <p className="mt-1 text-xs text-slate-500">{walls.size} camada(s) marcada(s) como parede.</p>
              </>
            )}
          </Card>

          <div className="md:col-span-2">
            <Card title="5. Blocos que o dicionário não reconhece">
              <p className="mb-2 text-xs text-slate-500">
                Associe blocos do desenho a uma classe do dicionário (ex.: <code>HR HID</code> → Hidrante). Os blocos
                não reconhecidos na última análise aparecem no resultado com o botão “mapear”.
              </p>
              {Object.keys(overrides).length > 0 && (
                <ul className="mb-2 space-y-1 text-sm">
                  {Object.entries(overrides).map(([block, cls]) => (
                    <li key={block} className="flex flex-wrap items-center gap-2">
                      <code className="rounded bg-slate-100 px-1">{block}</code> →
                      <select value={cls} onChange={(e) => setOverrides({ ...overrides, [block]: e.target.value })}
                        aria-label={`Classe do bloco ${block}`} className="rounded border border-slate-300 px-1 py-0.5">
                        <option value="">escolha…</option>
                        {opts?.classes.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                      </select>
                      <button type="button" className="text-xs text-red-700 underline"
                        onClick={() => { const { [block]: _, ...rest } = overrides; setOverrides(rest); }}>remover</button>
                    </li>
                  ))}
                </ul>
              )}
              <div className="flex gap-2">
                <input value={newBlock} onChange={(e) => setNewBlock(e.target.value)} placeholder="Nome do bloco"
                  aria-label="Nome do bloco" className="rounded border border-slate-300 px-2 py-1 text-sm" />
                <Button type="button" variant="ghost" disabled={!newBlock.trim()}
                  onClick={() => { setOverrides({ ...overrides, [newBlock.trim()]: "" }); setNewBlock(""); }}>
                  Adicionar
                </Button>
              </div>
            </Card>
          </div>

          <div className="flex flex-wrap items-center gap-3 md:col-span-2">
            {opts && opts.packages.length > 1 && (
              <select value={packageId} onChange={(e) => setPackageId(e.target.value)} aria-label="Pacote de regras"
                className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                {opts.packages.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.rules} regras)</option>)}
              </select>
            )}
            <Button type="submit" disabled={blocked || create.isPending}>
              {create.isPending ? "Enviando…" : "Analisar planta"}
            </Button>
            {Object.values(overrides).some((v) => !v) && (
              <span className="text-xs text-amber-800">Blocos sem classe escolhida serão ignorados.</span>
            )}
            {create.error && <ErrorState error={create.error} />}
          </div>
        </form>

        <Card title="Análises desta planta">
          {history.error && <ErrorState error={history.error} />}
          {history.data?.items.length === 0 && <EmptyState>Nenhuma análise ainda.</EmptyState>}
          <ul className="divide-y divide-slate-100">
            {history.data?.items.map((a) => (
              <li key={a.id}>
                <button
                  onClick={() => setParams({ analise: a.id })}
                  className={`w-full rounded px-2 py-2 text-left text-sm hover:bg-slate-50 ${current === a.id ? "bg-teal-50 ring-1 ring-teal-600/30" : ""}`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span>{new Date(a.created_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</span>
                    <ExecutionBadge state={a.state} />
                  </span>
                  <span className="block text-xs text-slate-500">
                    risco {a.context?.risk_class?.toLowerCase() ?? "não informado"}
                    {a.summary && " · " + STATUS_ORDER.filter((s) => a.summary!.by_status[s])
                      .map((s) => `${a.summary!.by_status[s]} ${STATUS_SHORT[s]}`).join(", ")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {current && (
        <div className="mt-6">
          <AnalysisResult
            analysisId={current}
            classes={opts?.classes ?? []}
            onMap={(block) => setOverrides((o) => (block in o ? o : { ...o, [block]: "" }))}
          />
        </div>
      )}
    </>
  );
}

function TriSelect({ label, value, onChange }: { label: string; value: Tri; onChange: (v: Tri) => void }) {
  return (
    <label className="flex items-center justify-between gap-2">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value as Tri)}
        className="w-40 rounded border border-slate-300 px-1 py-1">
        <option value="">não informado</option>
        <option value="sim">exigido</option>
        <option value="nao">não exigido</option>
      </select>
    </label>
  );
}
