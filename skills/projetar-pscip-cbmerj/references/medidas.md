# Medidas de segurança: como tratar cada uma

Gerado de `normative/projeto/medidas.yaml` (não editar à mão). É o mesmo roteiro que
`enquadrar_edificacao` devolve em `como_tratar`. A medida da tabela casa pelo início do
nome.

## Extintores

- **Situação:** CALCULA — o motor dimensiona e gera memorial
- **Ferramenta:** `dimensionar_extintores`
- **Ler:** `consultar_norma("NT 2-01")`
- **Símbolos:** `EXTINTOR_PQS_ABC`, `EXTINTOR_CO2`, `EXTINTOR_AP`, `EXTINTOR_PQS_ABC_SOBRERODAS`, `E-5`
- **Entrega:** quadro de extintores por pavimento, posição em planta, percurso conferido

## Hidrantes e mangotinhos

- **Situação:** CALCULA — o motor dimensiona e gera memorial
- **Ferramenta:** `dimensionar_hidrantes`
- **Ler:** `consultar_norma("NT 2-02")`, `consultar_norma("NT 2-04")`
- **Símbolos:** `HIDRANTE_SIMPLES`, `HIDRANTE_DUPLO`, `REGISTRO_RECALQUE`, `BOMBA_INCENDIO`, `RESERVA_TECNICA_INCENDIO`, `ACIONADOR_BOMBA_INCENDIO`
- **Entrega:** memorial hidráulico, RTI, esquema vertical (operação corte), casa de máquinas, recalque
- **O motor não cobre:** conjunto de pressurização (NT 2-04) e zonas de pressão são lidos na NT, não calculados

## Chuveiros automáticos

- **Situação:** CALCULA — o motor dimensiona e gera memorial
- **Ferramenta:** `dimensionar_sprinklers`
- **Ler:** `consultar_norma("NT 2-03 P1")`, `consultar_norma("NT 2-03 P2")`
- **Símbolos:** `BICO_SPRINKLER_PENDENTE`, `BICO_SPRINKLER_CIMA`, `VALVULA_GOVERNO_ALARME_VGA`, `REGISTRO_RECALQUE_SPRINKLER`
- **Entrega:** dispensas por ambiente, RTI (Q x t do Anexo B), VGA, shaft e recalque pela NT 2-03; malha de bicos, rede, hidráulica da área remota e isométrico (operações sprinklers e isometrico)
- **O motor não cobre:** a classe de risco, a densidade, a área de operação, a área por bico e o espaçamento vêm da ABNT NBR 10897 ou NFPA 13 (fora da base) e saem como premissa a conferir; armazenamento (NT 2-03 P2) é lido na NT; a hidráulica é simplificada (uma zona, uma subgeral)

## Sinalização de segurança

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-05")`
- **Símbolos:** `S-12`, `S-1`, `S-2`, `S-3`, `E-5`, `E-7`, `E-2`, `P-4`
- **Entrega:** placas de orientação e salvamento nas rotas, de equipamentos e de proibição/alerta, com dimensão pela distância de visualização (Tabela 7)
- **O motor não cobre:** quantidade e posição das placas, que o Claude define lendo a NT (o desenho de cada placa é o oficial da NT 2-05)

## Iluminação de Emergência

- **Situação:** REQUISITOS — o motor devolve só o que a NT fixa
- **Ferramenta:** `requisitos_iluminacao_alarme`
- **Ler:** `consultar_norma("NT 2-06")`
- **Símbolos:** `PONTO_ILUMINACAO_EMERGENCIA`, `PONTO_ILUMINACAO_EMERGENCIA_BALIZAMENTO`
- **Entrega:** pontos nas rotas, escadas e áreas comuns; autonomia; tipo de sistema
- **O motor não cobre:** espaçamento e iluminamento pela ABNT NBR 10898 (fora da base)

## Alarme de Incêndio

- **Situação:** REQUISITOS — o motor devolve só o que a NT fixa
- **Ferramenta:** `requisitos_iluminacao_alarme`
- **Ler:** `consultar_norma("NT 2-07")`
- **Símbolos:** `ACIONADOR_MANUAL`, `AVISADOR_SONORO_ELETRONICO`, `AVISADOR_AUDIOVISUAL`, `CENTRAL_ALARME_DETECCAO`
- **Entrega:** acionadores a no máximo 30 m de percurso, avisadores, central, fonte secundária

## Detecção de Incêndio

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-07")`
- **Símbolos:** `DETECTOR_FUMACA`, `DETECTOR_TERMICO`, `DETECTOR_TERMOVELOCIMETRICO`, `CENTRAL_ALARME_DETECCAO`
- **Entrega:** tipo de detector por ambiente e área de cobertura pela NT e pela ABNT NBR 17240
- **O motor não cobre:** NBR 17240 fora da base

## Saídas de Emergência

- **Situação:** CALCULA — o motor dimensiona e gera memorial
- **Ferramenta:** `dimensionar_saidas`
- **Ler:** `consultar_norma("NT 2-08")`, `consultar_norma("NT 2-09")`
- **Símbolos:** `ROTA_DE_FUGA_DIRECAO_FLUXO`, `ROTA_DE_FUGA_FINAL`, `BARRA_ANTIPANICO`, `S-12`
- **Entrega:** população, larguras, portas, escadas; tipo de escada pela observação da tabela e pelo Anexo B da NT 2-08; distância máxima conferida na planta
- **O motor não cobre:** detalhamento da escada (degraus, antecâmara, dutos) e pressurização (NT 2-09) lidos na NT

## Pressurização de escada

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-09")`
- **Entrega:** sistema de pressurização da escada e elevador de emergência conforme a NT

## Plano de emergência

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-10")`, `consultar_norma("NT 2-11")`
- **Entrega:** PECIP e, quando exigida, brigada de incêndio dimensionada pela NT 2-11

## SPDA

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-12")`
- **Entrega:** sistema de proteção contra descargas atmosféricas conforme a NT e a ABNT NBR 5419

## Controle de fumaça

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-14")`
- **Símbolos:** `VENTILADOR_EXAUSTOR_FUMACA`, `DAMPER_CORTA_FUMACA`, `ACIONADOR_EXAUSTAO_VENTILACAO`
- **Entrega:** sistema de controle de fumaça conforme a NT

## Ventilação e controle de gases e fumaça

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-14")`, `consultar_norma("NT 4-09")`
- **Entrega:** ventilação de túneis conforme as NTs

## Hidrante urbano

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-15")`
- **Símbolos:** `HIDRANTE_URBANO`, `HIDRANTE_URBANO_SUBTERRANEO`
- **Entrega:** posição do hidrante urbano e distância à edificação conforme a NT

## Acesso de viatura em edificações

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-16")`
- **Entrega:** via de acesso, portão, faixa de estacionamento e resistência do piso conforme a NT

## Compartimentação

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-18")`, `consultar_norma("NT 2-17")`
- **Símbolos:** `PORTA_CORTA_FOGO_P90`, `DAMPER_CORTA_FOGO`, `SHAFT_PROTEGIDO`
- **Entrega:** paredes e portas corta-fogo (operações parede/porta com estilo corta_fogo e corta_fogo_min), selagens de shafts, afastamentos de fachada

## Segurança Estrutural contra Incêndio

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-19")`
- **Entrega:** TRRF dos elementos estruturais conforme a NT

## Controle de Materiais de Acabamento

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 2-20")`
- **Entrega:** classes dos materiais de piso, parede e teto por ambiente conforme a NT

## Sistema de espuma

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 3-06")`
- **Símbolos:** `ESTACAO_FIXA_EMULSIONAMENTO`, `CANHAO_MONITOR_PORTATIL_ESPUMA`, `LIQUIDO_GERADOR_ESPUMA`
- **Entrega:** sistema de espuma conforme a NT de líquidos inflamáveis e combustíveis

## Sistema de Resfriamento

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 3-06")`
- **Símbolos:** `CANHAO_MONITOR_RESFRIAMENTO`
- **Entrega:** sistema de resfriamento de tanques conforme a NT

## Sistema de comunicação

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Ler:** `consultar_norma("NT 4-09")`
- **Entrega:** comunicação de emergência em túneis conforme a NT

## Controle de

- **Situação:** LER_NT — sem cálculo: ler a NT e registrar as exigências
- **Entrega:** controle de temperatura, de fontes de ignição e de pós em silos — ver as observações da Tabela 29 e a nota técnica específica
