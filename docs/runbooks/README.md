# Runbooks

| Situação | Procedimento |
|---|---|
| DXF com unidade desconhecida | Execução fica `WAITING_INPUT` / `DRAWING_UNIT_UNCONFIRMED`. Confirmar unidade na preparação (CAD-02) com uma medida de referência conhecida. |
| XRef ausente | Reenviar o pacote com a XRef como `XREF_DXF`. O motor não busca arquivos fora do pacote. |
| Cancelar job | Botão cancelar ou `POST /v1/executions/{id}/cancel`. Em execução → `CANCEL_REQUESTED`; o supervisor encerra o worker. |
| PC reiniciou no meio de um job | Abrir o motor: jobs com lease vencido voltam à fila com `WORKER_INTERRUPTED`. Nada é marcado como sucesso. |
| Liberar temporários | Encerrar o motor e abrir de novo: temporários órfãos são removidos. `jobs/staging` pode ser limpo com o motor fechado. Originais nunca são apagados automaticamente. |
| Restaurar backup | `scripts\restore\restore.ps1 -Backup <pasta> -Target <pasta vazia>`; abrir com `COSCIP_DATA_DIR` apontando para a restauração, conferir projeto e relatório, só então substituir a base ativa. |
| Configurar/revogar chave de IA | Configurações → credenciais (fica no cofre do Windows). Remover localmente **não** revoga no fornecedor: revogar também no painel do provedor. |
| Limite de gastos atingido | Tarefas de IA restantes vão para revisão humana. Aumentar o teto é decisão explícita do operador. |
| Reverter atualização | Versões instaladas lado a lado; voltar à anterior só com o backup feito antes da migração. |
| Regra publicada com erro | Bloquear novas execuções da versão, listar análises atingidas, preservar documentos antigos, criar reanálise vinculada. |
| Disco cheio | Upload recusado com `DISK_SPACE_LOW` (reserva de 5× o tamanho). Estágio em andamento é cancelado com diagnóstico. |
