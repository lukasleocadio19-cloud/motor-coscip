import { Card, NotYet, PageHeader } from "@coscip/ui";

export function HistoryPage() {
  return (
    <>
      <PageHeader title="Histórico" />
      <Card>
        <NotYet backlog="REV-02">
          Arquivos, modelos e resultados por revisão; abrir análise antiga com o modelo e as regras
          da época. Comparação automática entre revisões é futura (FUT-02).
        </NotYet>
      </Card>
    </>
  );
}
