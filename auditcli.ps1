$d = "$env:TEMP\cli-audit"
if (Test-Path $d) { Remove-Item $d -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory $d | Out-Null
Copy-Item "C:\Users\jusaper\Downloads\coolqml-rs\cli\*" $d -Recurse -Force
Copy-Item "$env:TEMP\cooltest-sync\cli\accounts.json" $d; Copy-Item "$env:TEMP\cooltest-sync\cli\cookies" $d -Recurse
"# group: a`n# category: a`nhttps://www.coolenglish.edu.tw/course/view.php?id=1`n" | Set-Content "$d\urls.txt"
Set-Location $d; $env:PYTHONUTF8 = "1"
$cases = @(
 @{n="-v"; a=@("-v"); i=""}, @{n="-h"; a=@("-h"); i=""},
 @{n="-h -l"; a=@("-h","-l"); i=""}, @{n="-h -g"; a=@("-h","-g"); i=""}, @{n="-h -u"; a=@("-h","-u"); i=""},
 @{n="-h -t"; a=@("-h","-t"); i=""}, @{n="-h -n"; a=@("-h","-n"); i=""}, @{n="-h -c"; a=@("-h","-c"); i=""},
 @{n="-h -s"; a=@("-h","-s"); i=""}, @{n="-h passwd"; a=@("-h","passwd"); i=""}, @{n="-h sudo"; a=@("-h","sudo"); i=""},
 @{n="-s"; a=@("-s"); i=""}, @{n="-H"; a=@("-H"); i=""},
 @{n="-a"; a=@("-a"); i="`n"}, @{n="-A"; a=@("-A"); i=""},
 @{n="-t"; a=@("-t"); i=""}, @{n="-t --raw"; a=@("-t","--raw"); i=""}, @{n="-t extra"; a=@("-t","x"); i=""},
 @{n="-n"; a=@("-n"); i="`n"}, @{n="-n 1"; a=@("-n"); i="1`n`n"},
 @{n="-c set"; a=@("-c","set","title","GREEN"); i=""}, @{n="-c set term"; a=@("-c","set","terminal_background_color","#101f20"); i=""},
 @{n="-u"; a=@("-u"); i="`n"}, @{n="-u -w"; a=@("-u","-w"); i="`n"},
 @{n="-g (list)"; a=@("-g"); i="`n"}, @{n="-g a"; a=@("-g","a"); i="`n"}, @{n="-g zz"; a=@("-g","zz"); i=""},
 @{n="-l cancel"; a=@("-l"); i="`n"}, @{n="--login"; a=@("--login"); i="`n"},
 @{n="passwd"; a=@("passwd"); i="`n"}, @{n="sudo -t"; a=@("sudo","-t"); i="`n"}, @{n="sudo (none)"; a=@("sudo"); i=""},
 @{n="REPL"; a=@(); i="-v`n/clear`n-t && -v`n/exit`n"}, @{n="REPL help"; a=@(); i="help`n-h`n/exit`n"},
 @{n="bogus"; a=@("--bogus"); i=""}, @{n="/exit"; a=@("/exit"); i=""},
 @{n="--version"; a=@("--version"); i=""}, @{n="--go"; a=@("--go"); i="`n"}, @{n="--time"; a=@("--time"); i=""},
 @{n="--url"; a=@("--url"); i="`n"}, @{n="--name"; a=@("--name"); i="`n"}, @{n="--account"; a=@("--account"); i="`n"}, @{n="--ALL"; a=@("--ALL"); i=""}
)
$k=0
foreach ($c in $cases) {
  $k++; $inf = "$d\_in$k.txt"; [IO.File]::WriteAllText($inf, $c.i)
  $p = Start-Process python -ArgumentList (@("cool.py") + $c.a) -RedirectStandardInput $inf -RedirectStandardOutput "$d\_out.txt" -RedirectStandardError "$d\_err.txt" -PassThru -NoNewWindow
  $done = $p.WaitForExit(40000)
  if (-not $done) { $p.Kill(); $st = "HANG" } else { $st = "exit=" + $p.ExitCode }
  $out = (Get-Content "$d\_out.txt" -Raw -Encoding UTF8) + (Get-Content "$d\_err.txt" -Raw -Encoding UTF8)
  $tb = if ($out -match "Traceback") { "TRACEBACK" } else { "" }
  $lines = ($out -split "`r?`n" | Where-Object { $_.Trim() -ne "" -and $_ -notmatch "\[  OK  \]|環境檢查|\[ SKIP|DEPEND" })
  "=== [$($c.n)] $st $tb"
  ($lines | Select-Object -Last 5) -join "`n"
}
