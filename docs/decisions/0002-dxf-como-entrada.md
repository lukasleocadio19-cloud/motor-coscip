# ADR 0002 — DXF é a entrada analítica

**Status:** aceita · 19/09/2026

**Decisão.** DXF com entidades suportadas é a única entrada analítica do MVP. DWG é guardado
como documento de origem; o DXF correspondente é solicitado ao projetista ou exportado por
ferramenta já licenciada.

**Motivo.** ezdxf é MIT e suficiente para o perfil inicial. O ODA File Converter restringe
não membros a uso não comercial; LibreDWG (GPLv3+) tem limitações que exigem corpus.

**Consequências.**
- Upload de `.dwg` como `ANALYTIC_DXF` → `422 UNSUPPORTED_DWG_INPUT`, ação `EXPORT_DXF`.
- Registrar DWG original, DXF derivado, ferramenta/versão e mapa de perdas.
- Handles do DXF não são tratados como handles originais do DWG.
- LibreDWG: experimento futuro (FUT-03).
