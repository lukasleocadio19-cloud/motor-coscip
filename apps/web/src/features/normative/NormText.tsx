/**
 * Mostra o trecho de uma NT convertida para Markdown: tabelas com pipes viram tabela,
 * marcadores de página e figuras viram avisos. Só texto (sem HTML vindo da fonte).
 */

type Block =
  | { kind: "p"; text: string }
  | { kind: "h"; text: string }
  | { kind: "page"; text: string }
  | { kind: "figure"; text: string }
  | { kind: "table"; rows: string[][] };

function cells(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

function parse(text: string): Block[] {
  const out: Block[] = [];
  let para: string[] = [];
  let table: string[][] | null = null;
  const flushPara = () => {
    if (para.length) out.push({ kind: "p", text: para.join(" ") });
    para = [];
  };
  const flushTable = () => {
    if (table) {
      // Descarta colunas vazias em todas as linhas (sobras da conversão do PDF).
      const width = Math.max(...table.map((r) => r.length));
      const keep = [...Array(width).keys()].filter((i) => table!.some((r) => (r[i] ?? "") !== ""));
      const rows = table.map((r) => keep.map((i) => r[i] ?? "")).filter((r) => r.some((c) => c));
      if (rows.length) out.push({ kind: "table", rows });
    }
    table = null;
  };
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (line.startsWith("|")) {
      flushPara();
      if (/^\|?\s*:?-{2,}/.test(line.replace(/\s/g, "").replace(/^\|/, ""))) continue; // separador
      (table ??= []).push(cells(line));
      continue;
    }
    flushTable();
    if (!line || line === "---") {
      flushPara();
      continue;
    }
    const page = line.match(/^##\s+P[áa]gina\s+(\d+)/);
    if (page) {
      flushPara();
      out.push({ kind: "page", text: `Página ${page[1]}` });
      continue;
    }
    if (/^!\[/.test(line)) {
      flushPara();
      out.push({ kind: "figure", text: line.match(/^!\[([^\]]*)\]/)?.[1] || "Figura" });
      continue;
    }
    if (/^#{1,6}\s/.test(line)) {
      flushPara();
      out.push({ kind: "h", text: line.replace(/^#+\s*/, "") });
      continue;
    }
    if (/^>\s?/.test(line)) continue; // notas da conversão
    para.push(line.replace(/\*\*/g, "").replace(/(\s*\|)+\s*$/, ""));
  }
  flushTable();
  flushPara();
  return out;
}

export function NormText({ text }: { text: string }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed text-slate-800">
      {parse(text).map((b, i) => {
        switch (b.kind) {
          case "p":
            return <p key={i}>{b.text}</p>;
          case "h":
            return <p key={i} className="font-semibold text-slate-900">{b.text}</p>;
          case "page":
            return <p key={i} className="border-t border-dashed border-slate-300 pt-1 text-xs text-slate-500">{b.text} do PDF</p>;
          case "figure":
            return (
              <p key={i} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
                {b.text} — imagem no PDF oficial (não convertida em texto)
              </p>
            );
          case "table":
            return (
              <div key={i} className="overflow-x-auto">
                <table className="min-w-full border-collapse text-xs">
                  <tbody>
                    {b.rows.map((r, j) => (
                      <tr key={j} className="border-b border-slate-200">
                        {r.map((c, k) => <td key={k} className="px-2 py-1 align-top">{c}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
        }
      })}
    </div>
  );
}
