# Replaces the single-file EXPERT.exe with a new release and restarts it.
# Started by the app, which first copies this script to its data folder: the .exe's own bundle
# folder is deleted when the app closes. User data lives in %LOCALAPPDATA%\EXPERT and is untouched.
param(
    [Parameter(Mandatory = $true)][string]$ExePath,  # the EXPERT.exe to replace
    [Parameter(Mandatory = $true)][string]$Url,      # the new EXPERT.exe (a GitHub release asset)
    [string]$WaitPids = '',                          # comma-separated app processes to wait for
    [string]$Log = ''
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # Invoke-WebRequest is far faster without the progress bar
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Host.UI.RawUI.WindowTitle = 'EXPERT update'
if (-not $Log) { $Log = Join-Path $env:TEMP 'EXPERT-update.log' }

function Say([string]$msg) {
    Write-Host $msg
    Add-Content -Path $Log -Value "$(Get-Date -Format s)  $msg"
}

$new = "$ExePath.new"
try {
    Say '== EXPERT update =='
    if ($Url -notlike 'https://github.com/oryanzz/EXPERT/releases/download/*') { throw "unexpected download URL: $Url" }

    Say 'Downloading the new version...'
    Invoke-WebRequest -Uri $Url -OutFile $new -UseBasicParsing -Headers @{ 'User-Agent' = 'EXPERT-updater' }
    if ((Get-Item $new).Length -lt 10MB) { throw 'the download looks incomplete' }

    # The single-file exe runs as a launcher + the app; the launcher holds the file until it exits.
    foreach ($id in ($WaitPids -split ',' | Where-Object { $_ })) {
        $p = Get-Process -Id ([int]$id) -ErrorAction SilentlyContinue
        if ($p) { Say 'Waiting for EXPERT to close...'; $p.WaitForExit(30000) | Out-Null }
    }
    for ($i = 1; $i -le 20; $i++) {
        try { Move-Item -Path $new -Destination $ExePath -Force; break }
        catch { if ($i -eq 20) { throw }; Start-Sleep -Milliseconds 500 }
    }

    Say 'Update complete.'
    Start-Process -FilePath $ExePath
    Start-Sleep -Seconds 2
} catch {
    Say "Update failed: $_"
    Remove-Item -Path $new -Force -ErrorAction SilentlyContinue
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("The update failed:`n$_`n`nDetails: $Log", 'EXPERT update') | Out-Null
    if (Test-Path $ExePath) { Start-Process -FilePath $ExePath }
    exit 1
}
