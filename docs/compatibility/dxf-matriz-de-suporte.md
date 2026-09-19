# Matriz de suporte DXF (inicial)

Fonte no código: `packages/cad/coscip_cad/dxf_reader.py` (`SUPPORT`). Ajustar com o corpus da POC.

| Entidade | Qualidade | Observação |
|---|---|---|
| LINE, LWPOLYLINE, POLYLINE | SUPPORTED | pontos transformados para o mundo |
| ARC, CIRCLE | SUPPORTED | escala não uniforme deixa de ser círculo: registrar erro de aproximação |
| INSERT + ATTRIB | SUPPORTED | expansão recursiva com caminho de instâncias; profundidade ≤ 16 |
| TEXT, MTEXT | SUPPORTED | texto extraído; sanitizar antes de exibir em HTML |
| HATCH | INVENTORY_ONLY | |
| POINT, ATTDEF solto, OLE2FRAME, IMAGE, ARC_DIMENSION | INVENTORY_ONLY | vistos no corpus de 19/09 |
| DIMENSION, LEADER, MULTILEADER | INVENTORY_ONLY | fonte documental; texto da cota ≠ medida real |
| SPLINE, ELLIPSE | VISUAL_ONLY | testes de compatibilidade específicos |
| SOLID, WIPEOUT | VISUAL_ONLY | preenchimentos 2D e máscaras |
| REGION, ACAD_PROXY_ENTITY, 3D, demais | UNSUPPORTED | inventariados, nunca descartados em silêncio |

Limites do perfil de teste: DXF ≤ 50 MB e 100 mil entidades antes da expansão;
`max_expanded_entities` = 2 000 000 (configurável).

XRefs: só dentro do pacote enviado com manifesto. Nunca seguir caminhos locais, compartilhamentos
ou URLs encontrados no desenho.

## Lições do corpus inicial (19/09/2026, 5 projetos)

- `$INSUNITS` estava errado ou ausente em **5 de 5** desenhos (todos em metros). A unidade
  declarada vira só indício; `coscip_cad.unit_evidence` sugere a unidade pelas cotas.
- Só o Model é analisado; pranchas com geometria própria geram aviso.
- Tamanho em MB não prediz custo: 63 MB → 7,5 s; 30 MB → 20,6 s. Limitar por entidades expandidas.
- Pior caso medido: 134 mil entidades expandidas, 20,6 s, 271 MB (i7-3770, 16 GB).
