# Updates EXPERT in place to the latest GitHub release (or runs `git pull` for a git checkout).
# Keeps your data: shots\, history.csv, sounds\done.wav, settings (.webview) and the .venv.
param(
    [int]$WaitPid = 0,     # the running app's process id: wait for it to close first
    [switch]$Restart,      # start EXPERT again when done
    [string]$Tag = ''      # install a specific release tag instead of the latest
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repo = 'oryanzz/EXPERT'
$log = Join-Path $root 'update.log'
$headers = @{ 'User-Agent' = 'EXPERT-updater' }
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Host.UI.RawUI.WindowTitle = 'EXPERT update'

function Say([string]$msg) {
    Write-Host $msg
    Add-Content -Path $log -Value "$(Get-Date -Format s)  $msg"
}

function Start-App {
    Start-Process -FilePath (Join-Path $root '.venv\Scripts\pythonw.exe') `
        -ArgumentList ('"' + (Join-Path $root 'app.py') + '"') -WorkingDirectory $root
}

function Get-RunningApp {
    $app = Join-Path $root 'app.py'
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains($app) }
}

try {
    Say '== EXPERT update =='

    # Files in use can't be replaced, so EXPERT must be closed first.
    if ($WaitPid) {
        $p = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
        if ($p) { Say 'Waiting for EXPERT to close...'; $p.WaitForExit(30000) | Out-Null }
    }
    if (Get-RunningApp) {
        Say 'Please close EXPERT to continue...'
        while (Get-RunningApp) { Start-Sleep -Seconds 1 }
    }

    if (Test-Path (Join-Path $root '.git')) {
        Say 'Git checkout found: running git pull'
        git -C $root pull --ff-only
        if ($LASTEXITCODE) { throw 'git pull failed' }
    } else {
        $api = if ($Tag) { "https://api.github.com/repos/$repo/releases/tags/$Tag" }
               else { "https://api.github.com/repos/$repo/releases/latest" }
        $release = Invoke-RestMethod -Uri $api -Headers $headers
        $tagName = $release.tag_name
        Say "Downloading EXPERT $tagName..."
        $tmp = Join-Path $env:TEMP ('expert-update-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $tmp | Out-Null
        try {
            $zip = Join-Path $tmp 'expert.zip'
            Invoke-WebRequest -Uri "https://github.com/$repo/archive/refs/tags/$tagName.zip" `
                -OutFile $zip -UseBasicParsing -Headers $headers
            Expand-Archive -Path $zip -DestinationPath $tmp
            $src = (Get-ChildItem -Path $tmp -Directory | Select-Object -First 1).FullName
            Say 'Installing the new files (your history, screenshots and settings are kept)...'
            # The release zip holds only program files, so copying over the folder never touches user data.
            robocopy $src $root /E /NFL /NDL /NJH /NJS /NP | Out-Null
            if ($LASTEXITCODE -ge 8) { throw "copying files failed (robocopy $LASTEXITCODE)" }
        } finally {
            Remove-Item -Path $tmp -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Say 'Updating dependencies...'
    & (Join-Path $root '.venv\Scripts\python.exe') -m pip install --disable-pip-version-check --quiet `
        -r (Join-Path $root 'requirements.txt')
    if ($LASTEXITCODE) { throw 'installing dependencies failed' }

    # Refresh the desktop shortcut only if it belongs to this install
    $desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'EXPERT.lnk'
    if (Test-Path $desktopLink) {
        $target = (New-Object -ComObject WScript.Shell).CreateShortcut($desktopLink).TargetPath
        if ($target -like "$root\*") { & (Join-Path $root 'scripts\make_shortcut.ps1') | Out-Null }
    }

    Say 'Update complete.'
    if ($Restart) { Start-App }
    Start-Sleep -Seconds 2
} catch {
    Say "Update failed: $_"
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("The update failed:`n$_`n`nDetails are in update.log.", 'EXPERT update') | Out-Null
    if ($Restart -and -not (Get-RunningApp)) { Start-App }
    exit 1
}
