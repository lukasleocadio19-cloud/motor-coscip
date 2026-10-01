# Fluxo digital e validação CAD — referência operacional

## Portal

1. Identificar solicitação e requerimento eletrônico.
2. Conferir DAEM e pagamento antes de reconhecer abertura válida.
3. Inventariar todos os uploads e confrontá-los com o Termo de Aceite.
4. Confirmar envio do termo em até sete dias; ausência encerra automaticamente a
   solicitação conforme as Notas DGST 149/2025 e 001/2026.
5. Controlar bilhete, reentrada, versão substituída e status `Pronto`.

Desde 01/02/2026, a análise de projeto novo é exclusivamente digital. A Nota DGST
001/2026 admite `.dwg` ou `.dwf`. Esta regra posterior prevalece sobre a extensão
exclusivamente `.dwg` do AAST 01/2025.

## Checklist CAD obrigatório

| Teste | Resultado esperado |
| --- | --- |
| Integridade | arquivo abre sem recovery impeditivo |
| Extensão | DWG ou DWF |
| Unicidade | todas as pranchas e complementares no arquivo |
| Model Space | escala real 1:1 |
| Unidade | m, cm ou mm, declarada e coerente |
| Organização | plantas identificadas e sequenciais |
| Layouts | um layout por prancha, nome e ordem coerentes |
| Paper Space | papel e escala configurados no layout |
| Planificação | desenhos 2D; registrar objetos não planificados |
| Quadro Resumo | inserido no projeto digital |
| Carimbos | responsáveis, registros, órgão e cadastro CBMERJ quando aplicável |
| Cores | vermelho sistemas de extinção; verde orientação/salvamento; azul iluminação; roxo detecção/alarme; laranja demais sinais/sistemas; preto arquitetura |
| Referências | fontes, imagens e XREFs resolvidos ou incorporados |
| Versão | hash vinculado à rodada e ao Termo de Aceite |

## Limite de automação

Sem conversor/leitor CAD que preserve layouts, viewports, cores, blocos, unidades e
geometria, registrar `não verificável`. Não declarar que o DWG foi medido apenas com base
em textos extraídos ou em pré-visualização raster.

Para cada medida geométrica, guardar: entidade/camada, layout, viewport, unidade,
coordenadas ou percurso, método de cálculo e tolerância. Medição raster não substitui
geometria vetorial.
