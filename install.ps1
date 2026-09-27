# Installs /apply into Claude Code on Windows.
#   powershell -ExecutionPolicy Bypass -File install.ps1
# Copies the skills and agents into ~/.claude (overwriting any existing skills/agents with the same names),
# installs the docx library build.js needs, and creates your data folder ($env:APPLY_HOME or ~/job-hunt).
param([string]$ClaudeDir = (Join-Path $HOME '.claude'))
$ErrorActionPreference = 'Stop'
$dataDir = if ($env:APPLY_HOME) { $env:APPLY_HOME } else { Join-Path $HOME 'job-hunt' }

foreach ($cmd in 'node', 'npm', 'python') {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "$cmd isn't on your PATH. Install it and run this again." }
}
if (-not [Type]::GetTypeFromProgID('Word.Application')) {
    throw "Microsoft Word isn't installed. /apply exports CVs to PDF through Word."
}

$skills = Join-Path $ClaudeDir 'skills'
$agents = Join-Path $ClaudeDir 'agents'
New-Item -ItemType Directory -Force $skills, $agents | Out-Null
foreach ($s in 'apply', 'apply-setup') {
    $dest = Join-Path $skills $s
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item -Force (Join-Path $PSScriptRoot "skills\$s\*") $dest
}
Copy-Item -Force (Join-Path $PSScriptRoot 'agents\*.md') $agents

Push-Location (Join-Path $skills 'apply')
try { npm install --no-audit --no-fund --loglevel=error docx@9 | Out-Null } finally { Pop-Location }

New-Item -ItemType Directory -Force (Join-Path $dataDir 'applications') | Out-Null

Write-Host "Installed /apply and /apply-setup into $ClaudeDir"
Write-Host "Your job-hunt data will live in $dataDir"
Write-Host "Next: open Claude Code and run /apply-setup. Have your current CV (PDF or DOCX) ready."
