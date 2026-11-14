# Exemplo: restaurante de 400 m² (F-8) — projeto fictício

Projeto **fictício**, feito para exercitar o motor de ponta a ponta. Os desenhos não têm valor
normativo: são rascunho, sem responsável técnico. As premissas (ocupação F-8, um pavimento,
pé-direito, telhado, lote e ruas, 4 x P-45 de GLP, alturas de bloco e abrigo) são do exemplo, não
de um cliente.

`saidas/` guarda o que cada etapa gerou (DXF do motor com o `.coscip.json` das operações, DWG,
PDF das pranchas e memoriais). `scripts/` guarda como cada saída foi gerada; todos gravam em
`saidas/`. Rode pelo `.venv` do projeto, na ordem:

| Script | Gera | O que mostra |
|---|---|---|
| `rodar3.py` | `restaurante-400m2.dxf`, `-memorial.md` | planta, análise e memorial de cálculo |
| `build_pdf.py` (+ `render_dxf.py`) | `-projeto-incendio.pdf` | primeiras pranchas em PDF |
| `cad_completo.py` | `-completo.dxf/.dwg` | planta, cortes e fachadas em camadas |
| `restaurante_d1.py` | `-d1.dxf` | camadas, estilos, janelas, cotas em cadeia |
| `restaurante_d2d3.py` | `-d2d3.dxf/.pdf` | chamadas de placa, mobiliário, folha A1 |
| `restaurante_d4.py` | `-d4.dxf/.pdf` | Quadro Resumo no modelo do CBMERJ |
| `restaurante_d5.py` | `-d5.dxf/.dwg/.pdf` | cortes e fachadas derivados da planta |
| `restaurante_e.py` | `-e.dxf/.dwg/.pdf`, `-sprinklers-memorial.md` | sprinklers e isométrico |
| `restaurante_f.py` | `-f.dxf/.pdf` | telhado, figura humana, classes NT 2-20, situação |
| `detalhes_g.py` | `-g.dxf/.pdf`, `detalhes-exemplo.*` | detalhes de instalação e de GLP |

```
.venv\Scripts\python.exe -I exemplos\restaurante-400m2\scripts\detalhes_g.py
```

Os DWG exigem o ODA File Converter (`COSCIP_ODA_PATH`); sem ele, os scripts que exportam DWG
param nessa etapa. O verificador de sobreposição usado nas entregas acusou 0 nas pranchas 03 a 06
de `-g` e em `detalhes-exemplo`.
