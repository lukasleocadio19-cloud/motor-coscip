# Contrato de dados do processo

## Identificação

`processo_id`, `requerimento_id`, `tipo_solicitacao`, `fase`, `data_protocolo`,
`unidade`, `status_portal`, `data_corte_normativa`, `snapshot_documental`,
`snapshot_normativo`.

## Lote

Para cada arquivo: `arquivo_id`, `nome_recebido`, `nome_original`, `hash_sha256`,
`tamanho`, `tipo`, `paginas/layouts`, `data_upload`, `versao`, `substitui`,
`assinatura_tipo`, `assinatura_status`, `atos_internos`.

## Papéis

Para cada pessoa/empresa: `id`, `papel`, `nome`, `registro`, `documento`,
`poder_representacao`, `fonte`, `validade`. Admitir vários papéis, sem fundi-los:
titular, proprietário, concessionário, arrendante, arrendatário, locatário, responsável,
administrador, procurador, requerente, RT, empresa técnica, signatário e pagador.

## Objeto espacial

`endereco_normalizado`, `coordenadas`, `lote`, `bloco`, `pavimento`, `unidade`,
`parte_ou_todo`, `poligono`, `atc`, `areas_parciais`, `vinculo_ato_anterior`.

## Parâmetros

`ocupacoes_por_ambiente`, `risco`, `carga_incendio`, `altura`, `pavimentos`,
`populacao`, `estoques`, `riscos_especificos`, `medidas_declaradas`,
`medidas_derivadas`, `medidas_projetadas`.

Todo valor guarda: literal, normalizado, unidade, arquivo, página/layout/camada,
responsável, data, nível de prova e confiança.
