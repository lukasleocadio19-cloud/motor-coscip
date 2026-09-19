# Restaura em pasta SEPARADA e vazia; confira antes de substituir a base ativa.
#   scripts\restore\restore.ps1 -Backup E:\BackupsCoscip\motor-coscip-backup-... -Target C:\CoscipRestaurado
param([Parameter(Mandatory)][string]$Backup, [Parameter(Mandatory)][string]$Target)
$root = Resolve-Path "$PSScriptRoot\..\.."
& "$root\.venv\Scripts\python.exe" -m coscip_api.cli restore $Backup $Target
