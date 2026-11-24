param([int[]]$Pages = @(0,1,2,3,4,5), [string]$Term = "", [string]$Seed = "")
$root = "C:\Users\jusaper\Downloads\coolqml-rs"
$tmp = Join-Path $env:TEMP "cooltest-run"
if (-not (Test-Path $tmp)) { New-Item -ItemType Directory $tmp | Out-Null }
New-Item -ItemType Directory -Force "$tmp\data","$tmp\cli" | Out-Null
$env:COOL_DATA_DIR = "$tmp\data"; $env:COOL_CLI_DIR = "$tmp\cli"
if ($Seed -ne "") { Copy-Item "$Seed\*" "$tmp\data" -Recurse -Force }
foreach ($pg in $Pages) {
  $env:COOL_SHOT = "1"; $env:COOL_SHOT_PAGE = "$pg"; $env:COOL_SHOT_OUT = "$tmp\shot$pg.png"
  if ($Term -ne "") { $env:COOL_SHOT_TERM = "1" } else { Remove-Item Env:COOL_SHOT_TERM -ErrorAction SilentlyContinue }
  $p = Start-Process -FilePath "$root\build-main\coolqml.exe" -PassThru -WorkingDirectory "$root\build-main"
  $null = $p.WaitForExit(45000); if (-not $p.HasExited) { $p.Kill() }
}
Get-ChildItem $tmp\*.png | Select-Object Name, Length, LastWriteTime
Get-Content "$root\build-main\host.log" -Tail 12
