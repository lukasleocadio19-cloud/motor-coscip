---
name: cbmerj-grupo-5-eventos
description: "Analisar reunião de público e eventos pelas NTs do Grupo 5 do CBMERJ: centros esportivos/eventos/exibição, eventos pirotécnicos, carros alegóricos/trios elétricos/carros de som, eventos temporários e atendimento médico. Usar diretamente ou quando $orquestrar-analise-cbmerj identificar EvRP, reunião de público permanente ou temporária."
---

# CBMERJ - Grupo 5

Executar o módulo para centros de reunião de público e para eventos temporários. Manter separados o processo da edificação permanente, a configuração temporária do evento e os riscos adicionais de cada edição.

## Iniciar

1. Ler [references/indice-grupo-5.md](references/indice-grupo-5.md).
2. Fixar a versão normativa e conferir o portal oficial se a consulta for posterior a 23/07/2026.
3. Identificar natureza do processo: local permanente, evento temporário, pirotecnia, veículo especial ou atendimento médico.
4. Registrar datas, duração, horários, público estimado/máximo, método de controle, setores, perfil do público e leiaute.
5. Vincular cada entrada a FARE, planta, memorial, contrato, laudo, ART/RRT/TRT e demais documentos apresentados.
6. Ler [references/roteiros-por-modalidade.md](references/roteiros-por-modalidade.md) e manter uma linha de base própria para cada edição/configuração do evento.

## Selecionar referências

- [NT 5-01](references/nt-5-01-centros-esportivos-eventos-e-exibicao.md): centros esportivos, de eventos e de exibição; conferir imagens.
- [NT 5-02](references/nt-5-02-eventos-pirotecnicos.md): eventos pirotécnicos; conferir imagens.
- [NT 5-03](references/nt-5-03-carros-alegoricos-trios-eletricos-e-carros-de-som.md): carros alegóricos, trios elétricos e carros de som; conferir imagens.
- [NT 5-04](references/nt-5-04-eventos-temporarios-de-reuniao-de-publico.md): eventos temporários de reunião de público; conferir imagens.
- [NT 5-05](references/nt-5-05-atendimento-medico-para-eventos.md): atendimento médico para eventos; conferir imagens.

## Executar por configuração

1. Confirmar aplicabilidade e prazo/procedimento correspondente ao evento.
2. Calcular população por setor e confrontar público declarado, área útil, assentos, ingressos e barreiras de controle.
3. Recalcular quantidade e largura das saídas, percursos, fluxos, descarga e capacidade das rotas.
4. Conferir setorização, barreiras, gradis, palcos, arquibancadas, estruturas temporárias, acessos operacionais e áreas restritas.
5. Dimensionar medidas de segurança, brigada, comunicação, sinalização, iluminação, extintores, hidrantes e atendimento médico conforme os gatilhos.
6. Para pirotecnia, conferir produto, quantidade, distância, isolamento, lançamento, responsável e interface com armazenamento/comércio.
7. Para carros alegóricos, trios e carros de som, conferir dimensões, lotação, instalações, materiais, rotas e documentação do veículo/estrutura.
8. Comparar FARE, planta, memorial, laudos, contratos e responsabilidades técnicas; registrar qualquer divergência.
9. Acionar Grupo 3 para GLP/GN, motogeradores, cozinha, líquidos ou outro risco específico e Grupo 4 para estrutura/atividade especial.
10. Quando a NT remeter materialmente a ABNT, Inmetro, fabricante ou outra fonte externa, registrar referência e edição, obter a fonte autorizada e nunca reconstruir a regra por memória. Sem o conteúdo necessário, retornar `dependência_externa_não_disponível` e bloquear conformidade integral.

Pesquisas úteis:

```bash
rg -n -i "população|lotação|saída|largura|setor|barreira" references/nt-5-01-centros-esportivos-eventos-e-exibicao.md
rg -n -i "distância|isolamento|lançamento|produto|quantidade" references/nt-5-02-eventos-pirotecnicos.md
rg -n -i "público|FARE|prazo|saída|brigada|estrutura" references/nt-5-04-eventos-temporarios-de-reuniao-de-publico.md
rg -n -i "posto médico|ambulância|profissional|público" references/nt-5-05-atendimento-medico-para-eventos.md
```

## Retornar ao orquestrador

Para cada configuração:

| Campo | Conteúdo |
| --- | --- |
| Evento/local | Tipo, datas, duração e configuração |
| Gatilho | Condição que tornou a NT aplicável |
| População | Critério, setores, cálculo e controle |
| Saídas | Quantidade, largura, percurso e capacidade |
| Estruturas | Palcos, arquibancadas, gradis, veículos e áreas temporárias |
| Medidas | Sistemas, brigada, comunicação e atendimento médico |
| Documentos | FARE, planta, memorial, contrato, laudo e responsabilidade técnica |
| Resultado | Conforme, não conforme, pendente ou não aplicável |
| Interface | Grupos 2, 3 ou 4 que alteram a conclusão |
| Fonte | NT, item/tabela e página |
| Saneamento | Correção ou documento necessário |

Não emitir autorização global. Quando o público, leiaute, datas, estruturas, riscos ou documentos estiverem indeterminados ou divergentes, retornar `pendente` e impedir a conclusão automática.
