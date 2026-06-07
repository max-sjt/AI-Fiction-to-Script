$ErrorActionPreference = "SilentlyContinue"

$ports = 6380, 8088, 8099
foreach ($port in $ports) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        Stop-Process -Id $listener.OwningProcess -Force
    }
}

$tempRoot = Join-Path $env:TEMP "ai-fiction-to-script-localstack"
$stagedNginx = Get-Process | Where-Object { $_.ProcessName -eq "nginx" -and $_.Path -like "$tempRoot*" }
if ($stagedNginx) {
    $stagedNginx | ForEach-Object { Stop-Process -Id $_.Id -Force }
}

Write-Output "Stopped local Memurai/App/Nginx stack on ports 6380, 8099, 8088."
