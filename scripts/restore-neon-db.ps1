param(
    [Parameter(Mandatory = $true)]
    [string]$DumpPath,
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrlSync
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command pg_restore -ErrorAction SilentlyContinue)) {
    throw "pg_restore was not found on PATH. Install PostgreSQL client tools first."
}

if (-not (Test-Path $DumpPath)) {
    throw "Dump path not found: $DumpPath"
}

Write-Host "Restoring $DumpPath into Neon target..."
pg_restore --dbname $DatabaseUrlSync --clean --if-exists --no-owner --no-acl $DumpPath

Write-Host "Restore complete."
