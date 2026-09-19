import { useEffect, useRef } from "react";
import { PlanViewer } from "@coscip/viewer";
import { Card, NotYet, PageHeader, StatusBadge } from "@coscip/ui";

/** Layout da análise (plano §12): camadas | planta | resultado selecionado; lista embaixo. */
export function AnalysisPage() {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!host.current) return;
    const viewer = new PlanViewer(host.current);
    const onResize = () => viewer.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      viewer.dispose();
    };
  }, []);

  return (
    <>
      <PageHeader title="Análise" />
      <nav className="mb-4 flex gap-4 text-sm" aria-label="Etapas">
        {["Preparação", "Análise", "Revisão", "Histórico", "Relatório"].map((t) => (
          <span key={t} className={t === "Análise" ? "font-semibold text-teal-800" : "text-slate-500"}>{t}</span>
        ))}
      </nav>
      <div className="grid gap-4 lg:grid-cols-[200px_1fr_280px]">
        <Card title="Camadas e filtros">
          <p className="text-xs text-slate-500">Desligar uma camada não a exclui da análise.</p>
        </Card>
        <div ref={host} className="h-[480px] rounded-lg border border-slate-200 bg-white" aria-label="Planta navegável" />
        <Card title="Resultado selecionado">
          <p className="text-sm text-slate-500">Selecione um achado na planta ou na lista.</p>
        </Card>
      </div>
      <div className="mt-4">
        <Card title="Lista de resultados">
          <div className="mb-3 flex flex-wrap gap-2">
            <StatusBadge status="PASS" />
            <StatusBadge status="FAIL" />
            <StatusBadge status="REVIEW_REQUIRED" />
            <StatusBadge status="NOT_APPLICABLE" />
            <StatusBadge status="MISSING_DATA" />
            <StatusBadge status="UNSUPPORTED" />
          </div>
          <NotYet backlog="VIEW-01 / REG-04">
            Cena progressiva do snapshot e resultados do pacote normativo congelado.
          </NotYet>
        </Card>
      </div>
    </>
  );
}
