import { Card, NotYet, PageHeader } from "@coscip/ui";

export function PreparationPage() {
  return (
    <>
      <PageHeader title="Preparação da planta" />
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="1. Unidade e referencial">
          <NotYet backlog="CAD-02">Confirmar unidade; sem confirmação, cálculos dependentes ficam bloqueados.</NotYet>
        </Card>
        <Card title="2. Recorte do pavimento">
          <NotYet backlog="PREP-01">Um pavimento por análise; regiões fora do recorte não entram nas medidas.</NotYet>
        </Card>
        <Card title="3. Classificação assistida">
          <NotYet backlog="PREP-02">Ambientes, aberturas, saídas e extintores, com origem e confirmação por propriedade.</NotYet>
        </Card>
        <Card title="4. Contornos analíticos">
          <NotYet backlog="PREP-03">Ajustes criam novo snapshot; o original é preservado.</NotYet>
        </Card>
      </div>
    </>
  );
}
