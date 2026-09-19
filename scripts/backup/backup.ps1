# Backup consistente para o destino cadastrado (use outro dispositivo).
#   scripts\backup\backup.ps1 -SetDestination E:\BackupsCoscip -Label "HD externo"
#   scripts\backup\backup.ps1
param([string]$SetDestination, [string]$Label)
$root = Resolve-Path "$PSScriptRoot\..\.."
$py = "$root\.venv\Scripts\python.exe"
if ($SetDestination) {
    & $py -m coscip_api.cli set-backup-destination $SetDestination --label $Label
    exit $LASTEXITCODE
}
& $py -m coscip_api.cli backup
