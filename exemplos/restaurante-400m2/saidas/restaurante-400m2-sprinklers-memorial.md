# Memorial dos sprinklers - restaurante fictício de 400 m²

> RASCUNHO sem valor normativo: parâmetros não homologados e sem responsável técnico. O projeto precisa de profissional habilitado (ART/RRT) e da conferência das normas.

## Chuveiros automáticos / sprinklers (NT 2-03 parte 1)

**Dados de entrada**

- classe_de_risco: ORDINARIO_1
- norma_adotada: NBR 10897
- resposta: PADRAO
- tubo: ACO
- grupo_divisao: F-8

**Memorial**

1. **Critérios de projeto (norma adotada)**: densidade_mm_min: 6,1; area_de_operacao_m2: 139; area_maxima_por_bico_m2: 12,1; espacamento_maximo_m: 4,6
   - Nota: a NT 2-03, 5.1.1, manda seguir a ABNT NBR 10897 (ou a NFPA 13 se a NBR não tratar do assunto) para classificação do risco, área de operação e demais parâmetros
2. **Ambientes e dispensas**: ambiente: SALÃO DE REFEIÇÕES; area_m2: 179,28; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 15, ambiente: COZINHA; area_m2: 57,04; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 5, ambiente: ESTOQUE SECO; area_m2: 18,4; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 2, ambiente: RECEBIMENTO / CÂMARA FRIA; area_m2: 35,8; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 3, ambiente: WC MASCULINO; area_m2: 19,7; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: WC FEMININO; area_m2: 19,7; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: WC PCD; area_m2: 10,1; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: DML; area_m2: 10,1; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: CIRCULAÇÃO; area_m2: 19,4; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 2
   - Base: NT 2-03 P1, 5.2.1, p. 4
   - Nota: decisão por ambiente conforme o tipo informado pelo projetista
3. **Área protegida**: 309,92 m²
   - Fórmula: `soma das áreas dos ambientes que levam bicos`
4. **Número mínimo de bicos**: 27 un
   - Fórmula: `Σ ⌈área do ambiente ÷ área máxima por bico⌉`
   - Nota: mínimo teórico por área: o número real vem da malha (espaçamento, paredes e obstruções) e é maior
5. **Vazão mínima em cada bico da área de operação**: 73,81 L/min
   - Fórmula: `q = densidade × área por bico`
   - Valores: densidade = 6,1; area_por_bico_m2 = 12,1
6. **Pressão no bico remoto**: 0,851 bar
   - Fórmula: `P = (q ÷ K)², não menor que a pressão mínima`
   - Valores: q_lpm = 73,81; K = 80; pressao_minima_bar = 0,5
7. **Vazão mínima do sistema (sem perdas)**: 885,7 L/min
   - Fórmula: `Q = bicos da área de operação × q`
   - Valores: bicos_na_area = 12
8. **Rede da zona Salão**: zona: Salão; orientacao_dos_ramais: x; bicos: 15; ramais: 3; espacamento_entre_bicos_m: 3,32; espacamento_entre_ramais_m: 3,6; area_por_bico_m2: 11,952; bicos_em_operacao: 12; area_de_operacao_m2: 143,42; vazao_do_bico_remoto_lpm: 72,91; pressao_do_bico_remoto_bar: 0,831; vazao_total_lpm: 1037,5; pressao_na_base_da_prumada_bar: 2,432; pressao_na_base_da_prumada_mca: 24,8; perdas_bar: ramal: 1,277; subgeral: 0,391; geral: 0,074; prumada: 0,079; estatica: 0,314; vga: 0,3; comprimento_por_dn_m: DN25: 6,64; DN32: 9,96; DN40: 17,96; DN50: 16,56; DN65: 3,6; DN80: 6,2; distancia_maxima_ao_bico_m: 2,39
   - Nota: cálculo hidráulico da área de operação remota (bicos em cascata, Hazen-Williams); simplificado
9. **Rede da zona Cozinha**: zona: Cozinha; orientacao_dos_ramais: x; bicos: 6; ramais: 2; espacamento_entre_bicos_m: 4,133; espacamento_entre_ramais_m: 2,3; area_por_bico_m2: 9,507; bicos_em_operacao: 6; area_de_operacao_m2: 57,04; vazao_do_bico_remoto_lpm: 57,99; pressao_do_bico_remoto_bar: 0,525; vazao_total_lpm: 383,3; pressao_na_base_da_prumada_bar: 1,547; pressao_na_base_da_prumada_mca: 15,77; perdas_bar: ramal: 0,468; subgeral: 0,055; geral: 0,041; prumada: 0,085; estatica: 0,314; vga: 0,3; comprimento_por_dn_m: DN25: 8,27; DN32: 8,27; DN40: 5,83; DN50: 4,75; distancia_maxima_ao_bico_m: 2,33
   - Nota: cálculo hidráulico da área de operação remota (bicos em cascata, Hazen-Williams); simplificado
10. **Reserva técnica de incêndio dos sprinklers (RTI)**: 31125 L
   - Fórmula: `RTI = Q × t`
   - Valores: Q_lpm = 1037,5; t_min = 30; categoria = ORDINARIO
   - Base: NT 2-03 P1, Anexo B - Tabela 1, p. 9
   - Nota: com mais de uma classificação de risco, vale a vazão e o tempo do maior risco (5.4.2)
11. **Pressão exigida na base da prumada (zona mais desfavorável)**: 24,8 mca
   - Fórmula: `soma das perdas até a prumada + altura estática + perda da VGA`
   - Valores: zona = Salão; vazao_lpm = 1037,5
12. **Material da tubulação**: ACO
   - Base: NT 2-03 P1, 5.3.1, p. 5
   - Nota: tubos não enterrados: aço, cobre ou CPVC (CPVC só com Risco Leve e bicos FR)
13. **Dispositivos de bloqueio, controle e alarme**: uma válvula de governo e alarme (VGA) na coluna de alimentação (definição 4.14; obrigatória quando o nível mínimo da RTI fica abaixo do teto mais alto, 5.5.5)
   - Base: NT 2-03 P1, 5.5.1, p. 5
14. **Hidrante de recalque dos sprinklers**: 2 saídas Storz de 2½" (63 mm), sinalizado "SPRINKLER" (Anexo C)
   - Base: NT 2-03 P1, 5.7.3, p. 7
   - Nota: recalque único para hidrantes e sprinklers: "HIDRANTE/SPRINKLER"; vários sistemas: inscrição adicional (Bloco 1/Bloco 2...)

**Resultados**

- classe_de_risco: ORDINARIO_1
- area_protegida_m2: 309,92
- bicos_minimos_por_area: 27
- bicos_na_area_de_operacao: 12
- vazao_do_sistema_lpm: 1037,5
- rti_sprinklers_l: 31125
- rti_total_l: 31125
- duracao_min: 30
- ambientes: ambiente: SALÃO DE REFEIÇÕES; area_m2: 179,28; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 15, ambiente: COZINHA; area_m2: 57,04; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 5, ambiente: ESTOQUE SECO; area_m2: 18,4; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 2, ambiente: RECEBIMENTO / CÂMARA FRIA; area_m2: 35,8; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 3, ambiente: WC MASCULINO; area_m2: 19,7; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: WC FEMININO; area_m2: 19,7; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: WC PCD; area_m2: 10,1; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: DML; area_m2: 10,1; decisao: DISPENSADO; motivo: banheiro, lavatório ou lavabo (NT 2-03, 5.2.3); bicos_minimos: 0, ambiente: CIRCULAÇÃO; area_m2: 19,4; decisao: PROTEGER; motivo: o sistema abrange toda a área da edificação (5.2.1); bicos_minimos: 2
- zonas: zona: Salão; orientacao_dos_ramais: x; bicos: 15; ramais: 3; espacamento_entre_bicos_m: 3,32; espacamento_entre_ramais_m: 3,6; area_por_bico_m2: 11,952; bicos_em_operacao: 12; area_de_operacao_m2: 143,42; vazao_do_bico_remoto_lpm: 72,91; pressao_do_bico_remoto_bar: 0,831; vazao_total_lpm: 1037,5; pressao_na_base_da_prumada_bar: 2,432; pressao_na_base_da_prumada_mca: 24,8; perdas_bar: ramal: 1,277; subgeral: 0,391; geral: 0,074; prumada: 0,079; estatica: 0,314; vga: 0,3; comprimento_por_dn_m: DN25: 6,64; DN32: 9,96; DN40: 17,96; DN50: 16,56; DN65: 3,6; DN80: 6,2; distancia_maxima_ao_bico_m: 2,39; avisos: , zona: Cozinha; orientacao_dos_ramais: x; bicos: 6; ramais: 2; espacamento_entre_bicos_m: 4,133; espacamento_entre_ramais_m: 2,3; area_por_bico_m2: 9,507; bicos_em_operacao: 6; area_de_operacao_m2: 57,04; vazao_do_bico_remoto_lpm: 57,99; pressao_do_bico_remoto_bar: 0,525; vazao_total_lpm: 383,3; pressao_na_base_da_prumada_bar: 1,547; pressao_na_base_da_prumada_mca: 15,77; perdas_bar: ramal: 0,468; subgeral: 0,055; geral: 0,041; prumada: 0,085; estatica: 0,314; vga: 0,3; comprimento_por_dn_m: DN25: 8,27; DN32: 8,27; DN40: 5,83; DN50: 4,75; distancia_maxima_ao_bico_m: 2,33; avisos: 
- simbolos: BICO_SPRINKLER_PENDENTE, VALVULA_GOVERNO_ALARME_VGA, REGISTRO_RECALQUE_SPRINKLER
- criterios: densidade_mm_min: 6,1; area_operacao_m2: 139; area_max_bico_m2: 12,1; espacamento_max_m: 4,6; k: 80

**Premissas do projetista (a norma não fixa)**

- densidade, area_operacao, area_bico, espacamento: valores de referência da NFPA 13:2019 (curvas densidade × área e espaçamento de bico padrão) como valor de referência; NÃO está na base do motor, para a classe ORDINARIO_1 (densidade 6.1 mm/min, área de operação 139 m², até 12.1 m² por bico e 4.6 m entre bicos). Conferir na norma adotada (NBR 10897) antes de usar.
- Fator K = 80 L/min/bar^½ (NT 2-03, 4.8, só define o fator), pressão mínima no bico 0.5 bar, C de Hazen-Williams 120, velocidade máxima 5 m/s, conexões 20 % do tubo reto e perda da VGA 0.3 bar: premissas do projetista (a NT não fixa).
- A hidráulica é a de uma zona retangular ou poligonal alimentada por uma subgeral, com tubo de aço classe 40 e diâmetros escolhidos por velocidade e perda unitária. Não trata de obstruções, vigas, desníveis internos nem de vários ramais ligados por laços: o projeto executivo usa o programa de cálculo do projetista.

**Pendências**

- Bomba de incêndio e conjunto de pressurização: escolher pela curva do fabricante no ponto (Q, pressão) acima, somando o desnível da água e as perdas da sucção; conjugado com hidrantes, atender aos dois sistemas (NT 2-04).
- Alarme de fluxo: o gongo hidráulico pode ser trocado por alarme elétrico supervisionado ligado ao alarme do prédio (5.5.6).
- Obstruções à descarga dos bicos, distância ao teto e ao deflector, proteção sob vigas e dutos: ABNT NBR 10897 (NT 2-03, 5.1.2).

**Verificar na planta**

- Cada ambiente que leva bicos tem malha respeitando o espaçamento e a área por bico; bicos fora dos ambientes dispensados.
- VGA, prumada e hidrante de recalque indicados e sinalizados (NT 2-05 E-10; Anexo C da NT 2-03).

**Base normativa conferida no texto**

- NT 2-03 P1, 5.2.1, p. 4 — O sistema abrange toda a área da edificação (exceções à parte)
- NT 2-03 P1, 5.2.3, p. 4 — Dispensa em banheiros, lavatórios e lavabos (vestiários não são dispensados); subestações, salas de medidores e de PC de energia até 20 m²
- NT 2-03 P1, Anexo B - Tabela 1, p. 9 — Duração da reserva técnica de incêndio dos sprinklers, por categoria de risco
- NT 2-03 P1, 5.4.2, p. 5 — RTI com mais de uma classificação de risco — vale a vazão e o tempo do maior risco
- NT 2-03 P1, 5.3.1, p. 5 — Tubos não enterrados - aço, cobre e CPVC (CPVC só em Risco Leve e só com bicos de resposta rápida)
- NT 2-03 P1, 5.5.1, p. 5 — Válvula de governo e alarme por coluna de alimentação; comando secundário por pavimento só onde a NT admite
- NT 2-03 P1, 5.7.3, p. 7 — Hidrante de recalque dos sprinklers — duas saídas Storz de 2½" (63 mm), sinalizado como "SPRINKLER"
