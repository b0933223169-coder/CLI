$ErrorActionPreference = 'Stop'
$src = 'C:\Users\jusaper\Downloads\coolqml-rs'
$dst = 'C:\Users\jusaper\Downloads\cool-qml-caelestia\coolqml\coolqml-rs'

New-Item -ItemType Directory -Force -Path $dst | Out-Null

# 原始碼 / 建置腳本 / helper scripts
$files = @(
  'main.cpp','backend.cpp','backend.h','color_engine.cpp','color_engine.h',
  'conpty.cpp','conpty.h','qml_pty_bridge.cpp','qml_pty_bridge.h','paths.h',
  'CMakeLists.txt','build_main.bat','deploy_main.bat',
  'fetch_report.py','check_cookie.py',
  'README.md'
)
foreach ($f in $files) {
  $p = Join-Path $src $f
  if (Test-Path $p) { Copy-Item -LiteralPath $p -Destination $dst -Force }
}

# 目錄：qml（含 our WebEngineView 版）、xterm、conpty 來源
foreach ($d in @('qml','xterm','conpty')) {
  $p = Join-Path $src $d
  if (Test-Path $p) { Copy-Item -LiteralPath $p -Destination $dst -Recurse -Force }
}

# 部署輸出 build-main（exe + Qt DLL + resources + conpty + qml modules）
Copy-Item -LiteralPath (Join-Path $src 'build-main') -Destination $dst -Recurse -Force

Write-Host "MIGRATED to $dst"
$s = (Get-ChildItem $dst -Recurse -File | Measure-Object -Sum Length).Sum
Write-Host ("size: {0:N0} MB" -f ($s/1MB))
