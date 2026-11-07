param(
  [ValidateSet('sqlite','mysql')][string]$Database='sqlite',
  [ValidateRange(1024,65535)][int]$Port=8010,
  [switch]$NoInstall
)
$ErrorActionPreference='Stop'
function Invoke-Checked {
  param([string]$Command,[string[]]$Arguments)
  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
}
Push-Location $PSScriptRoot
try {
  $venv=Join-Path $PSScriptRoot '.venv'
  $python=Join-Path $venv 'Scripts/python.exe'
  if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { Invoke-Checked py @('-3','-m','venv',$venv) }
    else { Invoke-Checked python @('-m','venv',$venv) }
  }
  if (-not $NoInstall) { Invoke-Checked $python @('-m','pip','install','-r','backend/requirements.txt') }
  $env:PYTHONPATH=Join-Path $PSScriptRoot 'backend'
  if ($Database -eq 'mysql') {
    Invoke-Checked docker @('compose','up','-d','--wait')
    if (-not $env:DATABASE_URL) { $env:DATABASE_URL='mysql+pymysql://career:career_local_only@127.0.0.1:3307/careerconnect?charset=utf8mb4' }
    if (-not $env:QDRANT_URL) { $env:QDRANT_URL='http://127.0.0.1:6335' }
  }
  Invoke-Checked $python @('-m','alembic','-c','backend/alembic.ini','upgrade','head')
  Invoke-Checked $python @('backend/scripts/seed_db.py')
  & $python backend/scripts/sync_vectors.py
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Vector sync incomplete. The backend worker will retry.' }
  Write-Host "Internship Connect: http://127.0.0.1:$Port/app/"
  Invoke-Checked $python @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$Port")
} finally { Pop-Location }
