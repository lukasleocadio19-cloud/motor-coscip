# DWG → DXF com ferramenta licenciada (POC-03)

Usado em 19/09/2026 com o AutoCAD 2027 instalado no PC. Sempre trabalhar sobre **cópias**.

Script `converter.scr` (uma linha por comando):

```
FILEDIA 0
_.DXFOUT "C:\caminho\saida.dxf" _V _2018 16
_.QUIT _Y
```

Execução sem interface (PowerShell):

```powershell
& "C:\Program Files\Autodesk\AutoCAD 2027\accoreconsole.exe" /i "C:\copias\projeto.dwg" /s converter.scr /l pt-BR
```

Registrar para cada arquivo: SHA-256 do DWG e do DXF, ferramenta/versão, comando e perdas
do log (ex.: `Substituindo [simplex.shx] para [...]` = só aparência de texto).

Não usar o ODA File Converter em uso profissional sem avaliar a licença (ADR 0002).
Não usar `Start-Process -Wait` com o accoreconsole: a espera pode não retornar; invocar direto com `&`.
