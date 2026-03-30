$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$port = 4175

Write-Host "Serving hexchess-board on http://127.0.0.1:$port/index.html"
Write-Host "Press Ctrl+C to stop."

python -m http.server $port --bind 127.0.0.1
