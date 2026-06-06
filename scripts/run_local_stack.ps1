$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $repoRoot "runtime"
$tempRoot = Join-Path $env:TEMP "ai-fiction-to-script-localstack"
$nginxRoot = Join-Path $tempRoot "nginx"
$memuraiData = Join-Path $tempRoot "memurai-data"
$memuraiExe = Join-Path $runtimeRoot "memurai\tools\memurai.exe"
$memuraiCliExe = Join-Path $runtimeRoot "memurai\tools\memurai-cli.exe"
$condaBat = (Get-Command conda -ErrorAction Stop).Source
$memuraiConf = Join-Path $tempRoot "memurai.conf"
$nginxConf = Join-Path $nginxRoot "conf\nginx.conf"
$redisPort = 6380
$appPort = 8099
$nginxPort = 8088

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
New-Item -ItemType Directory -Force -Path $memuraiData | Out-Null

$sourceNginxRoot = Join-Path $runtimeRoot "nginx\nginx-1.31.1"
if (Test-Path $nginxRoot) {
    Remove-Item -Recurse -Force -LiteralPath $nginxRoot
}
Copy-Item -Recurse -Force -LiteralPath $sourceNginxRoot -Destination $nginxRoot

$existingApp = Get-NetTCPConnection -LocalPort $appPort -State Listen -ErrorAction SilentlyContinue
if ($existingApp) {
    Stop-Process -Id $existingApp.OwningProcess -Force
}

$existingNginx = Get-NetTCPConnection -LocalPort $nginxPort -State Listen -ErrorAction SilentlyContinue
if ($existingNginx) {
    Stop-Process -Id $existingNginx.OwningProcess -Force
}

$existingRedis = Get-NetTCPConnection -LocalPort $redisPort -State Listen -ErrorAction SilentlyContinue
if ($existingRedis) {
    Stop-Process -Id $existingRedis.OwningProcess -Force
}

@"
bind 127.0.0.1
protected-mode yes
port $redisPort
dir $memuraiData
dbfilename dump.rdb
appendonly yes
appendfilename appendonly.aof
loglevel notice
logfile $memuraiData\memurai.log
save 900 1
save 300 10
save 60 10000
"@ | Set-Content -LiteralPath $memuraiConf -Encoding ASCII

Start-Process -FilePath $memuraiExe -ArgumentList $memuraiConf -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null
Start-Sleep -Seconds 2
& $memuraiCliExe -p $redisPort PING | Out-Null

$env:WEB_CACHE_ENABLED = "1"
$env:REDIS_URL = "redis://127.0.0.1:$redisPort/0"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c","""$condaBat"" run -n py312 python -m ai_fiction_to_script.cli web --host 127.0.0.1 --port $appPort" -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null
Start-Sleep -Seconds 3

@"
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    server {
        listen $nginxPort;
        server_name localhost;
        client_max_body_size 20m;

        location / {
            proxy_pass http://127.0.0.1:$appPort;
            proxy_http_version 1.1;
            proxy_set_header Host `$host;
            proxy_set_header X-Real-IP `$remote_addr;
            proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto `$scheme;
            proxy_connect_timeout 10s;
            proxy_send_timeout 180s;
            proxy_read_timeout 180s;
        }
    }
}
"@ | Set-Content -LiteralPath $nginxConf -Encoding ASCII

Push-Location $nginxRoot
& ".\nginx.exe" -p "$nginxRoot\"
Pop-Location

Write-Output "Memurai: 127.0.0.1:$redisPort"
Write-Output "App: http://127.0.0.1:$appPort"
Write-Output "Nginx: http://127.0.0.1:$nginxPort"
