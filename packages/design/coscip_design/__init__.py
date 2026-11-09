"""Dimensionamento do projeto de segurança contra incêndio e pânico (modo PROJETO do motor).

O motor nasceu para CONFERIR projetos (planta → evidência → achado). Este pacote faz o caminho
inverso: a partir dos dados da edificação, calcula o que a norma exige e devolve um **memorial
de cálculo** em que cada passo cita o item da norma, conferido no texto ingerido.

Regras herdadas do projeto:

- parâmetro cuja citação não confere no texto não é usado: o cálculo é recusado;
- o que a norma não fixa (rendimento da bomba, coeficiente da mangueira, comprimentos
  equivalentes) entra como **premissa do projetista**, listada à parte no memorial;
- nada tem valor normativo: rascunho, sem homologação e sem responsável técnico.
"""

from coscip_design.memorial import Memorial, Passo
from coscip_design.params import ParamError, Parametros, load_params

__all__ = ["Memorial", "ParamError", "Parametros", "Passo", "load_params"]
