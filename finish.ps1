# usage: .\finish.ps1 <tool> <task>
param([Parameter(Mandatory)][string]$Tool, [Parameter(Mandatory)][string]$Task)
$ErrorActionPreference = "Stop"
$K = $PSScriptRoot
$Root = if ($env:EVAL_RUNS) { $env:EVAL_RUNS } else { "C:\eval-runs" }
$Run = Join-Path $Root "$Tool\$Task"; $R = Join-Path $K "results\$Tool\$Task"
$sec = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [int64](Get-Content "$R\start")
$sec | Set-Content "$R\seconds"
git -C $Run add -A
git -C $Run diff --cached HEAD --binary --output="$R\changes.patch"
foreach ($f in "findings.json", "answers.md") { if (Test-Path "$Run\$f") { Copy-Item "$Run\$f" $R } }
Write-Host "Saved to $R ($sec s)."
$n = Read-Host "Notes (errors, got stuck, could not read the image, needed a retry...). Enter to skip"
if ($n) { $n | Set-Content -Encoding utf8 "$R\notes.txt" }
