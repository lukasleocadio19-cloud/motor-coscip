# Restaurante F-8 400 m2 - memorial de calculo (rascunho, projeto ficticio)

> RASCUNHO sem valor normativo: parâmetros não homologados e sem responsável técnico. O projeto precisa de profissional habilitado (ART/RRT) e da conferência das normas.

## Dados da edificação

- ocupacao: F-8 (local para refeição) - suposta a partir de 'restaurante'
- area_total_construida_m2: 400
- pavimentos: 1
- altura_m: 4,40 até o topo da platibanda (premissa); pé-direito 3,60
- tipo_de_construcao: BETA (premissa)
- area_para_populacao_m2: 350,48 (400 - sanitarios 49,52; NT 2-08 5.2.4)

## Saídas de emergência (NT 2-08)

**Dados de entrada**

- ocupacao: F-8

**Memorial**

1. **Térreo: população**: 351 pessoas
   - Fórmula: `P = área / 1`
   - Valores: area_m2 = 350,48; m2_por_pessoa = 1
2. **Térreo: acessos e descarga**: 2,2 m
   - Fórmula: `N = teto(P / C); largura = máx(N × 0,55; largura mínima)`
   - Valores: P = 351; C = 100; N = 4; largura_minima_m = 1,2
   - Base: NT 2-08, 5.3.1.2, p. 6; NT 2-08, 4.39, p. 5; NT 2-08, 5.3.1.3, p. 6
3. **Térreo: portas das rotas de saída**: 1 porta com vão ≥ 2,00 m em duas folhas (N = 4)
   - Fórmula: `N = teto(P / C); vão conforme N`
   - Valores: P = 351; C = 100; N = 4
   - Base: NT 2-08, 5.3.4.4, p. 7

**Resultados**

- quadro_por_pavimento: pavimento: Térreo; populacao: 351; unidades_de_passagem_acesso: 4; largura_minima_acessos_m: 2,2; unidades_de_passagem_portas: 4; portas: 1 porta com vão ≥ 2,00 m em duas folhas (N = 4)
- minimo_de_saidas: 2

**Premissas do projetista (a norma não fixa)**

- Áreas informadas já seguem 5.2.3 e 5.2.4 da NT 2-08 (o que entra e o que se exclui da área do pavimento) — responsabilidade de quem informou.

**Pendências**

- Térreo: lotação acima de 200 pessoas no grupo F → barra antipânico nas portas de saída (5.3.4.9).
- NT 2-08, 5.1 c: edificação de até 2 pavimentos isenta de escada enclausurada pode ter largura mínima de 0,80 m (não vale para C-3, F-1 a F-7, F-9 a F-11, H-2 e H-3). Aqui foi mantido 1,20 m: conferir se a redução se aplica.

**Verificar na planta**

- Distância máxima a percorrer até a saída (Anexo C da NT 2-08): analisar_planta mede o percurso; sem leiaute definido vale a distância direta com limite 30 % menor (5.3.3.3).
- Largura medida na parte mais estreita; portas abrindo no sentido da saída quando o ambiente passa de 100 pessoas (5.3.4.1).
- Sinalização de saída (NT 2-05) e iluminação de emergência nas rotas (NT 2-06).

**Base normativa conferida no texto**

- NT 2-08, Anexo A, p. 18 — População e capacidade da unidade de passagem — linha 'F-2, F-5, F-8'
- NT 2-08, 5.3.1.2, p. 6 — Número de unidades de passagem N = P/C (arredondado para cima)
- NT 2-08, 4.39, p. 5 — Largura da unidade de passagem
- NT 2-08, 5.3.1.3, p. 6 — Larguras mínimas de acessos, escadas e rampas
- NT 2-08, 5.3.4.4, p. 7 — Vão mínimo das portas por unidades de passagem
- NT 2-08, 5.3.4.9, p. 7 — Lotação acima da qual a divisão F exige barra antipânico
- NT 2-08, 5.3.2.7, p. 6 — Mínimo de saídas no grupo F


## Extintores de incêndio (NT 2-01)

**Dados de entrada**

- risco: MEDIO
- pavimentos: Térreo: 400 m²

**Memorial**

1. **Térreo: unidades extintoras pela área**: 3 un
   - Fórmula: `N = teto(área / área máxima por unidade)`
   - Valores: area_m2 = 400; area_max_m2 = 150
   - Base: NT 2-01, Tabela 3, p. 5
2. **Térreo: mínimo de extintores**: 2 un
   - Base: NT 2-01, 5.2.5, p. 4
   - Nota: um classe A e um classes B e C, ou dois de pó ABC
3. **Térreo: extintores das instalações especiais**: 2 un
   - Valores: instalacoes = Central de GLP, Quadro geral de energia elétrica
   - Base: NT 2-01, 6.4, p. 5
   - Nota: um por instalação, a no máximo 5 m dela; tipo conforme a NT ou a NBR da instalação

**Resultados**

- total_de_extintores: 5
- quadro_por_pavimento: pavimento: Térreo; area_m2: 400; por_area: 3; minimo: 2; adotado: 3; instalacoes_especiais: 2; total: 5
- tipo_sugerido: agente: PQS_ABC; simbolo: EXTINTOR_PQS_ABC; capacidade_minima: 2-A: 20-B: C; alternativa: um de água (2-A) + um de CO2 (5-B: C) ou pó BC (20-B: C)
- distancia_maxima_a_percorrer_m: 15
- altura_maxima_da_alca_m: 1,6

**Pendências**

- Classes D e K (metais pirofóricos, cozinha profissional) e depósitos de inflamáveis/GLP seguem notas específicas (NT 2-01 6.2 e 6.3): fora deste cálculo.

**Verificar na planta**

- Distância real a percorrer até o extintor ≤ 15 m em todos os pontos (analisar_planta mede o pior percurso); se passar, acrescentar extintores.
- Extintor junto aos acessos, visível, fora de escadas e sem obstrução (5.2.2).
- Placa E-5 em cada extintor (NT 2-05).

**Base normativa conferida no texto**

- NT 2-01, Tabela 3, p. 5 — Área máxima protegida por uma unidade extintora; Distância máxima a percorrer até o extintor
- NT 2-01, 5.2.5, p. 4 — Mínimo de extintores (um classe A e um classes B e C, ou dois ABC)
- NT 2-01, 6.4, p. 5 — Distância máxima do extintor à instalação especial (casa de máquinas, bombas, força…)
- NT 2-01, Tabela 1, p. 4 — Capacidade extintora mínima — extintores portáteis
- NT 2-01, 5.2.1, p. 4 — Altura máxima da alça de manuseio


## Iluminação de emergência (NT 2-06)

**Dados de entrada**

- ocupacao: F-8

**Memorial**

1. **Onde instalar**: escadas, halls de acesso às escadas, áreas de refúgio, demais áreas comuns e ao longo das rotas de saída
   - Base: NT 2-06, 5.1.2, p. 3
2. **Autonomia mínima**: 60 min
   - Base: NT 2-06, 5.2, p. 3
3. **Escadas**: no nível do pavimento e no nível do patamar intermediário, sem ponto de sombra
   - Base: NT 2-06, 5.3.2, p. 3

**Resultados**

- simbolo: PONTO_ILUMINACAO_EMERGENCIA
- autonomia_min: 60
- locais: escadas, halls de acesso às escadas, áreas de refúgio, demais áreas comuns e ao longo das rotas de saída

**Pendências**

- Espaçamento, nível de iluminamento e tipo de luminária seguem a ABNT NBR 10898 (NT 2-06, 5.1.1), que não está na base do motor: definir com o responsável técnico.

**Verificar na planta**

- Pontos ao longo de toda a rota de saída, nas mudanças de direção e nas portas de saída, sem ponto de sombra.

**Base normativa conferida no texto**

- NT 2-06, 5.1.2, p. 3 — Locais de instalação da iluminação de emergência
- NT 2-06, 5.2, p. 3 — Autonomia mínima da iluminação de emergência
- NT 2-06, 5.3.2, p. 3 — Pontos de iluminação nas escadas



## Cozinha profissional (NT 3-01) — projeto fictício, premissas do projetista

**Equipamentos de cocção (Tabela 1 da NT 3-01, p. 5, fonte ABNT NBR 14518):** fogão 6 bocas (moderado), chapa de grelhados (severo),
fritadeira (moderado) e forno combinado (moderado), todos a GLP e sob a mesma coifa. Como há equipamento moderado e severo sob o
mesmo captor, o sistema de exaustão é **Tipo I** (5.5.1; observação da Tabela 1: o mais crítico define).
**Edificação de economia única** (uma razão social; 5.6.1).

**Aplicabilidade (2.1 e 2.2, p. 3):** a NT só se aplica quando falta compartimentação, isto é, quando o duto (a) atravessa paredes, pisos
ou tetos e se comunica com outros ambientes ou (b) fica a menos de 1 m de aberturas da fachada. **Premissa do desenho:** um único duto vertical,
aparente, que sobe de dentro da cozinha direto à cobertura, sem passar por forro ou ambiente de outra finalidade, e sai pelo menos 1,0 m acima da laje, longe de
janelas (a janela mais próxima, J1, está a mais de 9 m). Nessa condição a cozinha é compartimentada (4.5) e a NT 3-01 não se aplica. **Isso precisa ser
confirmado pelo responsável técnico com o projeto de exaustão (NBR 14518, fora da base do motor).**

**Se o duto cruzar outro ambiente (Tipo I, economia única, Tabela 2, p. 5):** damper corta-fogo de acionamento eletromecânico (5.9.7 e 5.9.8: fechamento imediato,
estanque, resistência ≥ 60 min), selagem das travessias, proteção passiva do duto, extintor portátil e **dispensa de sistema fixo de extinção**. Em qualquer caso:
rede de dutos aparente, sem forro (5.9.1); aço carbono ≥ 1,37 mm ou inox ≥ 1,09 mm (5.9.3); trecho externo ≥ 1 m de qualquer abertura (5.9.4);
o duto não pode passar em compartimento com medidor ou botijão de gás (5.9.2 — a central de GLP é externa).

**Extintores da cozinha (5.9.9 da NT 3-01 e NT 2-01 6.2):** um de pó ABC junto à porta de acesso ao salão e **um extintor classe K** junto à linha de cocção
(a 4 m do fogão e dentro de 10 m de todos os equipamentos; Tabela 5 da NT 2-01: distância máxima 10 m). O dimensionamento da classe K é **a critério do
profissional autor do projeto** (NT 2-01 6.2.2): capacidade e agente (agente químico úmido) ficam como pendência.

## Central de GLP (NT 3-02, 2ª ed. 2023, alterada em 2025) — projeto fictício

| Item | Adotado | Base |
|---|---|---|
| Recipientes | 4 × P-45, trocáveis, em uma linha | 4.20; 5.3.4 e 5.3.5 |
| Massa / volume total | 180 kg / 0,432 m³ (4 × 0,108 m³) | 4.4; Anexo A, Tabela 2 (até 2,0 m³) |
| Localização | térreo, fora da projeção da edificação, ventilada, junto à fachada norte | 5.2.1 |
| Abrigo | 180 kg > 90 kg: paredes e cobertura com **TRRF ≥ 120 min** | 5.3.2 b |
| Dimensões internas | 2,00 × 1,60 m, altura útil ≥ 1,80 m, piso de concreto ≥ 0,05 m | 5.3.2 c, d |
| Abertura | lado maior (norte) totalmente aberto, com portas incombustíveis para fora; ventilação ≥ 10 % da planta (0,32 m²) | 5.3.2 e, f |
| Afastamento da edificação | 0 m (central ≤ 2,0 m³) | Anexo A, Tabela 2 |
| Aberturas e fontes de ignição | 1,5 m (trocáveis); com abrigo TRRF 120 interposto, pode cair à metade | Anexo A, Tabela 1 e obs. j |
| Ralos e caixas de gordura | ≥ 1,0 m (a caixa de gordura prevista está a mais de 8 m) | 5.2.5 |
| Passeio público | 3 m (ou metade, com abrigo TRRF 120) — **depende da implantação do lote, não definida** | Anexo A, Tabela 2 e obs. d |
| Extintores | capacidade total ≤ 270 kg: 1 × 20-B:C ou 1 × PQS 6 kg, a ≤ 10 m, sinalizado (E-5); previsto a cerca de 2 m | 5.4.1, 5.4.2, Tabela 3 |
| Hidrante da central | não exigido: a edificação não tem sistema de hidrantes | 5.4.3 |
| Resfriamento fixo e SPDA | não exigidos (< 10 m³; SPDA dispensado na central) | 5.4.4; 5.4.8 |
| Placa | PERIGO / GÁS INFLAMÁVEL / PROIBIDO FUMAR, 190 × 95 mm, fotoluminescente; desenhadas as placas P-1, A-2 e A-3 | 5.4.5 |
| Registro geral de corte | junto à central, fora da projeção da edificação | 6.2 |
| Outros materiais na central | proibidos | 5.1.7 |

**Pendências da central de GLP:** documento de responsabilidade técnica da execução da central, do ensaio de estanqueidade e das estruturas com TRRF 120 (5.3.9); ensaio de
estanqueidade da rede interna pela ABNT NBR 15358 e laudo (6.4); nota no Quadro Resumo informando abastecimento por central de GLP e representação em planta, corte e planta de
situação com quantidade, massa e volume dos recipientes e forma de abastecimento — trocável (8.2). A rede interna não é analisada pelo CBMERJ (8.4). Confirmar a distância ao limite do lote e a norma NBR 13523 (fora da base).

## Esquadrias e fachadas

A observação 4 da Tabela 2 do Anexo III refere-se a edificações sem janelas. O projeto prevê J1 e J2 (oeste) e J3 (sul), todas de 1,20 m de altura com peitoril de 0,90 m.
Como o motor não desenha janelas, elas aparecem como texto na planta e em desenho nas fachadas; confirmar a observação 4 com o analista.
