---
name: cbmerj-grupo-2-medidas-seguranca
description: "Dimensionar e conferir as medidas de segurança contra incêndio e pânico do Grupo 2 do CBMERJ: extintores, hidrantes, mangotinhos, sprinklers, bombas, sinalização, iluminação, detecção, saídas, pressurização, PECIP, brigadas, SPDA, gases, fumaça, hidrante urbano, acesso de viaturas, separação, compartimentação, TRRF e CMAR. Usar diretamente ou quando $orquestrar-analise-cbmerj solicitar o módulo de medidas."
---

# CBMERJ - Grupo 2

Executar somente as medidas do Grupo 2 acionadas pelo Decreto e pelo enquadramento recebido. Não presumir ocupação, risco ou exigência ausentes; solicitar o resultado do Grupo 1 ou registrar bloqueio.

## Iniciar

1. Ler [references/indice-grupo-2.md](references/indice-grupo-2.md).
2. Fixar a versão normativa e conferir o portal oficial se a consulta for posterior a 23/07/2026.
3. Receber: ocupações, risco, ATC, altura, pavimentos, população, carga de incêndio, sistemas exigidos, riscos específicos e evidências do projeto.
4. Para cada medida, separar exigência, dimensionamento, representação, documentação de CA e interfaces.
5. Ler [references/dependencias-externas-e-evidencias-ca.md](references/dependencias-externas-e-evidencias-ca.md) antes de afirmar completude normativa ou documental.

## Selecionar referências

- [NT 2-01](references/nt-2-01-extintores.md): extintores.
- [NT 2-02](references/nt-2-02-hidrantes-e-mangotinhos.md): hidrantes, mangotinhos, RTI e cálculo hidráulico.
- [NT 2-03 Parte 1](references/nt-2-03-parte-1-sprinklers-requisitos-gerais.md): sprinklers - requisitos gerais.
- [NT 2-03 Parte 2](references/nt-2-03-parte-2-sprinklers-armazenamento.md): sprinklers - armazenamento; conferir imagens.
- [NT 2-04](references/nt-2-04-conjunto-de-pressurizacao.md): bombas e pressurização.
- [NT 2-05](references/nt-2-05-sinalizacao.md): sinalização; conferir imagens.
- [NT 2-06](references/nt-2-06-iluminacao-de-emergencia.md): iluminação.
- [NT 2-07](references/nt-2-07-deteccao-e-alarme.md): detecção e alarme.
- [NT 2-08](references/nt-2-08-saidas-de-emergencia.md): população, larguras, distâncias e escadas; conferir imagens.
- [NT 2-09](references/nt-2-09-pressurizacao-de-escada.md): pressurização de escadas, elevadores, antecâmaras e refúgios.
- [NT 2-10](references/nt-2-10-pecip.md): PECIP.
- [NT 2-11](references/nt-2-11-brigadas-de-incendio.md): brigada, BVI e bombeiro civil.
- [NT 2-12](references/nt-2-12-spda.md): SPDA.
- [NT 2-13](references/nt-2-13-sistemas-fixos-de-gases.md): sistemas fixos de gases.
- [NT 2-14](references/nt-2-14-controle-de-fumaca.md): controle de fumaça; conferir imagens.
- [NT 2-15](references/nt-2-15-hidrante-urbano.md): hidrante urbano.
- [NT 2-16](references/nt-2-16-acesso-de-viaturas.md): acesso de viaturas.
- [NT 2-17](references/nt-2-17-separacao-entre-edificacoes.md): separação entre edificações.
- [NT 2-18](references/nt-2-18-compartimentacao.md): compartimentação horizontal e vertical.
- [NT 2-19](references/nt-2-19-seguranca-estrutural.md): TRRF e resistência ao fogo.
- [NT 2-20](references/nt-2-20-controle-de-materiais-de-acabamento.md): CMAR.

## Executar por medida

1. Confirmar o gatilho da exigência recebido do orquestrador.
2. Identificar todos os parâmetros de entrada e sua evidência.
3. Refazer cálculo verificável; não aceitar apenas o resultado declarado.
4. Conferir cobertura geométrica, percurso real, interferências, detalhes e compatibilidade entre sistemas.
5. Comparar planta, isométrico, memorial, planilha, curva, laudo e ART/RRT/TRT.
6. Conferir imagens quando houver tabela mesclada, símbolo, esquema ou fórmula complexa.
7. Acionar Grupo 3, 4 ou 5 quando o risco/estrutura/evento alterar o dimensionamento.
8. Executar um teste de consistência interna: conclusão declarada × memória de cálculo × tabela × desenho × quantidade/símbolo. Não escolher silenciosamente um valor divergente.
9. Em CA, distinguir projeto, instalação, inspeção, manutenção, ensaio e operacionalidade; exigir o tipo de evidência previsto na NT 1-01 e na NT da medida.

Pesquisas úteis:

```bash
rg -n -i "reserva técnica|vazão|pressão|perda de carga" references/nt-2-02-hidrantes-e-mangotinhos.md
rg -n -i "população|unidade de passagem|distância máxima|escada" references/nt-2-08-saidas-de-emergencia.md
rg -n -i "acantonamento|extração|admissão|vazão" references/nt-2-14-controle-de-fumaca.md
rg -n -i "TRRF|tempo requerido|redução" references/nt-2-19-seguranca-estrutural.md
```

## Retornar ao orquestrador

Para cada medida:

| Campo | Conteúdo |
| --- | --- |
| Medida | Sistema analisado |
| Aplicabilidade | Exigida, dispensada, condicionada ou não determinada |
| Entradas | Valores e evidências utilizadas |
| Regra/cálculo | Fórmula, tabela, hipótese e resultado recalculado |
| Projeto | Cobertura, geometria, detalhes e compatibilidade |
| Documentos | Memorial, planilha, laudo e responsabilidade técnica |
| Resultado | Conforme, não conforme, pendente ou não aplicável |
| Interface | Grupos 3, 4 ou 5 que alteram a conclusão |
| Fonte | NT, item/tabela e página |
| Saneamento | Correção ou documento necessário |

Não emitir conclusão global de aprovação. Quando faltar dado determinante, retornar `pendente` e informar exatamente qual entrada impede o cálculo.
