---
name: analise-eventos-completa-pdf
description: >
  Skill para análise completa de processos de Autorização de Eventos de Reunião de Público (EvRP).
  Executa a conferência documental, verificação de pranchas (PDF) de instalações efêmeras,
  avaliação do quadro resumo (público estimado), dimensionamento das medidas de segurança 
  e atendimento médico (NTs do Grupo 5).
---

# ANÁLISE DE PROCESSO PARA AUTORIZAÇÃO DE EVENTOS (EvRP)
## Protocolo: Documentação + Análise de Pranchas (Projetos Temporários em PDF)

Esta skill baseia-se na aplicação da legislação (Decreto 42/2018) e das Notas Técnicas dedicadas a eventos (NT 5-01, NT 5-02, NT 5-03, NT 5-04 e NT 5-05) para analisar e autorizar instalações efêmeras e temporárias para Reunião de Público.

---

## 🎪 FASE 1 — CONFERÊNCIA DOCUMENTAL DO EVENTO

Eventos exigem farta comprovação de responsabilidade sobre estruturas provisórias. Todo documento ausente é pendência:

1. **Requerimento e Declaração:** 
   - Verificar Razão Social, CNPJ da produtora, nome do evento, local exato e datas/horários.
2. **DAEM e Pagamento:**
   - DAEM deve possuir a receita correta de Evento/Vistoria provisória e taxa condizente com a antecedência do protocolo.
3. **Responsabilidade Técnica (ARTs/RRTs ou TRTs):**
   - **Projeto de SCIP do Evento.**
   - **Montagem de Estruturas Temporárias** (Palcos, arquibancadas, tendas, camarotes).
   - **Instalações Elétricas e Geradores** (Grupo gerador exige ART e laudo de aterramento/SPDA se aplicável).
   - **Trio Elétrico/Carro de Som** (Se Carnaval/Blocos - NT 5-02).
4. **Documentos de Autorização Local:**
   - "Nada Opor" do proprietário do espaço ou órgão público responsável pelo logradouro.
   - Contrato de locação da área.
5. **Declarações Adicionais:** Contrato de equipe médica (NT 5-05), brigadistas civis e seguranças.

---

## 👥 FASE 2 — AVALIAÇÃO DO QUADRO RESUMO DO EVENTO

A prancha PDF deve apresentar obrigatoriamente um **Quadro Resumo do Evento**:

1. **Público Estimado vs. Capacidade Máxima:** 
   - A planta deve explicitar a lotação. Divida a área livre pelo índice (ex: 2 a 3 pessoas/m² conforme o tipo de evento - pista, camarote c/ mesas, etc). O fator mais crítico deve reger o projeto.
2. **Caracterização:** 
   - Datas do evento, horário de início e fim.
   - Área ocupada total (m²).

---

## 📏 FASE 3 — ENQUADRAMENTO E DEFINIÇÃO DE MEDIDAS (SÉRIE NT 5)

1. **Sistemas e Dispositivos (NT 5-01):**
   - Risco provisório exige Extintores portáteis superdimensionados, Iluminação de emergência robusta (autônoma) ao redor da estrutura, e demarcação rigorosa de rotas.
2. **Dimensionamento de Lotação e Saídas (NT 2-08 aplicável a eventos):**
   - Cada portão/saída do evento precisa ter sua largura validada com base nas Unidades de Passagem (UPs) requeridas pelo público total.
3. **Plano Médico e Preventivo (NT 5-05):**
   - Cruzar o Público Estimado com as tabelas da NT 5-05 para exigir o quantitativo exato de: Postos Médicos (leitos), Ambulâncias (Básica e UTI), Médicos e Enfermeiros. 

---

## 🔍 FASE 4 — ANÁLISE TÉCNICA DAS PRANCHAS (PDF)

Confrontar as pranchas em formato PDF contra a teoria:

1. **Circulação e Fugas:**
   - Verificar largura de corredores, rotas até a saída de emergência ("vomitórios"). Verificar se barricadas ou fechamentos reduzem a rota para menos que o autorizado.
   - Setas indicativas de evacuação perfeitamente traçadas para a via pública.
2. **Disposição dos Extintores:**
   - Extintores posicionados próximos a geradores de energia, praças de alimentação (food trucks/cozinhas - tipo K ou BC), painéis de LED (C02), e distribuídos pela pista (Água e Pó/ABC).
3. **Layout Específico:**
   - Conferir distanciamento do público para os palcos, camarins e saídas.
   - Locais dos Postos Médicos sinalizados (fácil acesso para ambulâncias externa e internamente).
4. **Sinalização (NT 2-05 / NT 5-01):**
   - Indicação de placas suspensas (Sinalização de Rota de Fuga) visíveis acima de 2m de altura.

---

## 📋 FASE 5 — GERAÇÃO DA LISTA DE EXIGÊNCIAS

Todo processo que apresente falhas nas estruturas vitais propostas gera exigência objetiva.

### ESTRUTURA DO RESULTADO DA SKILL:

```text
==============================================================
RELATÓRIO DE ANÁLISE PARA AUTORIZAÇÃO DE EVENTO (EvRP)
==============================================================
Dados Consolidados do Evento:
- Nome/Local: [Evento - Local]
- Público Estimado Declarado: [Qtd]
- Profissional SCIP: [Nome]

--------------------------------------------------------------
[1] PENDÊNCIAS DOCUMENTAIS
- Indicar falta de ART (ex: ART de estabilidade das tendas ausente).
- Divergências de data ou público entre memorial e DAEM.

--------------------------------------------------------------
[2] MEDIDAS ESTRUTURAIS E SAÚDE (NT 5-05) E DIMENSIONAMENTO
- Dimensionamento obrigatório: [2] Médicos, [2] Ambulâncias, [30] Seguranças.
- Situação do projeto: [Atende / Falha em apresentar].

--------------------------------------------------------------
[3] EXIGÊNCIAS TÉCNICAS NAS PRANCHAS
Lista numerada para correção dos PDFs da planta:
1. Saídas de Emergência – NT 5-01: A largura das passagens no Portão A soma apenas 3m, mas para o público de setor exigiria-se 4,5m (8 UPs). Adequar planta.
2. Posicionamento de Extintores: Falta locar extintor CO2 próximo ao gerador (Prancha 01).

==============================================================
STATUS DO EVENTO: [COM EXIGÊNCIAS / APROVADO]
==============================================================
```
Regra: Nunca estimar saídas; aplique o rigor matemático. A vida em eventos depende de escape rápido.
