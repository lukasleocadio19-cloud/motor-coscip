# Empacotamento

Adiado até depois da prova de conceito (plano §13, FUT-09): o instalador não deve atrasar a
primeira planta funcionando.

Quando chegar a hora, o pacote deve conter:

- runtime Python 3.12 e dependências **travadas** (versões exatas testadas no Windows);
- `apps/api/coscip_api/static` já compilado (sem Node.js na máquina final);
- Chromium para PDF instalado e validado uma vez (REP-02);
- avisos de licença (ezdxf MIT, Shapely BSD, GEOS LGPL, SQLite domínio público, Three.js MIT…);
- manifesto de versões (esquema, engine, frontend) e hash do pacote do worker.

Instalar a versão nova **ao lado** da anterior; rollback de código não abre banco migrado
incompatível (SAFE-03).
