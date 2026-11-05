<#
Runs only against the disposable local Docker database. It does not run on production data.
#>
param([string]$BackupPath = "backups/phase-0-smoke.sql")

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path (Split-Path $BackupPath) | Out-Null
$restoreDatabase = "rpm_restore_smoke"
$containerBackup = "/tmp/rpm_restore_smoke.sql"
$created = $false

function Invoke-DockerCompose {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
  & docker compose @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose $Arguments failed with exit code $LASTEXITCODE"
  }
}

try {
  Invoke-DockerCompose exec -T postgres sh -c "pg_dump -U rpm -d rpm > $containerBackup"
  Invoke-DockerCompose cp "postgres:$containerBackup" $BackupPath
  Invoke-DockerCompose exec -T postgres dropdb -U rpm --if-exists $restoreDatabase
  Invoke-DockerCompose exec -T postgres createdb -U rpm $restoreDatabase
  $created = $true
  Invoke-DockerCompose cp $BackupPath "postgres:$containerBackup"
  Invoke-DockerCompose @('exec', '-T', 'postgres', 'psql', '-v', 'ON_ERROR_STOP=1', '-U', 'rpm', '-d', $restoreDatabase, '-f', $containerBackup)
  Invoke-DockerCompose @('exec', '-T', 'postgres', 'psql', '-v', 'ON_ERROR_STOP=1', '-U', 'rpm', '-d', $restoreDatabase, '-c', 'SELECT count(*) >= 0 AS restore_readable FROM users;')
  Write-Host "Backup/restore smoke test passed for disposable local data."
} finally {
  if ($created) {
    Invoke-DockerCompose exec -T postgres dropdb -U rpm --if-exists $restoreDatabase
  }
}
