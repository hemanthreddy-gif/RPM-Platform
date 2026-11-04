<#
Runs only against the disposable local Docker database. It does not run on production data.
#>
param([string]$BackupPath = "backups/phase-0-smoke.sql")

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path (Split-Path $BackupPath) | Out-Null
docker compose exec -T postgres pg_dump -U rpm -d rpm | Set-Content -NoNewline $BackupPath
docker compose exec -T postgres createdb -U rpm rpm_restore_smoke
Get-Content -Raw $BackupPath | docker compose exec -T postgres psql -U rpm -d rpm_restore_smoke
docker compose exec -T postgres psql -U rpm -d rpm_restore_smoke -c "SELECT 1;"
docker compose exec -T postgres dropdb -U rpm rpm_restore_smoke
Write-Host "Backup/restore smoke test passed for disposable local data."
