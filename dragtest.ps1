param([string]$Tag="a", [int]$Rounds=6, [string]$Dock="bottom")
$root="C:\Users\jusaper\Downloads\coolqml-rs"; $tmp="$env:TEMP\cooltest-run"
Get-Process coolqml -ErrorAction SilentlyContinue | Stop-Process -Force
"{`"terminalDock`":`"$Dock`"}" | Set-Content "$tmp\data\settings.json"; $env:COOL_DATA_DIR="$tmp\data"; $env:COOL_CLI_DIR="$tmp\cli"
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WT { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(int f,int x,int y,int d,int e); }
"@
function Click($x,$y){ [WT]::SetCursorPos($x,$y); Start-Sleep -Milliseconds 300; [WT]::mouse_event(2,0,0,0,0); [WT]::mouse_event(4,0,0,0,0); Start-Sleep -Milliseconds 2500 }
$p = Start-Process "$root\build-main\coolqml.exe" -PassThru -WorkingDirectory "$root\build-main"
Start-Sleep 8; $p.Refresh(); [WT]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
if ($Dock -eq "right") { Click 42 628; Start-Sleep 6 } else { Click 42 628; Start-Sleep 6 }
# find drawer top handle: scan by assuming 391 first time; afterwards handle moves, so drag from current top
$left = 833
for ($r=0; $r -lt $Rounds; $r++) {
  [WT]::SetCursorPos($left+4,400); Start-Sleep -Milliseconds 200; [WT]::mouse_event(2,0,0,0,0)
  $xs = if ($r % 2 -eq 0) { @(($left-30),($left-70),($left-110),($left-90),($left-130)) } else { @(($left+30),($left+60),($left+40),($left+90)) }
  foreach ($x in $xs) { [WT]::SetCursorPos($x+4,400); Start-Sleep -Milliseconds 70 }
  [WT]::mouse_event(4,0,0,0,0); Start-Sleep -Milliseconds 700
  $left = $xs[-1]
}
Start-Sleep 1
[WT]::SetCursorPos(1000,620); [WT]::mouse_event(2,0,0,0,0); [WT]::mouse_event(4,0,0,0,0)
[System.Windows.Forms.Clipboard]::SetText("PASTETEST123456"); Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("^+v"); Start-Sleep 2
$b=New-Object Drawing.Bitmap 1386,788; $g=[Drawing.Graphics]::FromImage($b); $g.CopyFromScreen(0,0,0,0,$b.Size); $b.Save("$tmp\drag_$Tag.png")
"alive $(-not $p.HasExited)"
