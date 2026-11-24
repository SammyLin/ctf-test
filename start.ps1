# usage: .\start.ps1 <tool> <task> [short|detailed]     cli: any name you choose, e.g. cli-a   task: audit b1 b2 v1 qa
param([Parameter(Mandatory)][string]$Tool, [Parameter(Mandatory)][string]$Task, [string]$Style = "detailed")
$ErrorActionPreference = "Stop"
$K = $PSScriptRoot
$Root = if ($env:EVAL_RUNS) { $env:EVAL_RUNS } else { "C:\eval-runs" }
$Run = Join-Path $Root "$Tool\$Task"; $R = Join-Path $K "results\$Tool\$Task"
if (Test-Path $Run) { throw "$Run already exists. Delete it to rerun." }
New-Item -ItemType Directory -Force $Run, $R | Out-Null
tar -xf (Join-Path $K "tasks\$Task.zip") -C $Run
git -C $Run init -q
git -C $Run config core.autocrlf false
git -C $Run add -A
git -C $Run -c user.email=eval@x -c user.name=eval commit -q -m snapshot
[DateTimeOffset]::UtcNow.ToUnixTimeSeconds() | Set-Content "$R\start"
$Style | Set-Content "$R\style"
Get-Content (Join-Path $K "prompts\$Task.$Style.txt") -Raw | Set-Clipboard
Write-Host "Timer started. Prompt is on the clipboard (also in prompts\$Task.$Style.txt)."
Write-Host "1) Open this folder in ${Tool}:  $Run"
Write-Host "2) New session, paste the prompt, let it work. Do not help it. 30 minute limit."
Write-Host "3) When it stops:  .\finish.ps1 $Tool $Task"
