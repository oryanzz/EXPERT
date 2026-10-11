# Creates an "EXPERT" shortcut that starts the app without a console window.
# Default location is the desktop; pass -Dir to put it somewhere else.
param([string]$Dir = [Environment]::GetFolderPath('Desktop'))

$root = Split-Path -Parent $PSScriptRoot
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path $Dir 'EXPERT.lnk'))
$link.TargetPath = Join-Path $root '.venv\Scripts\pythonw.exe'
$link.Arguments = '"' + (Join-Path $root 'app.py') + '"'
$link.WorkingDirectory = $root
$link.IconLocation = (Join-Path $root 'ui\icon.ico') + ',0'
$link.Description = 'EXPERT - EXP PER TIME'
$link.Save()
Write-Host "Shortcut created: $($link.FullName)"
