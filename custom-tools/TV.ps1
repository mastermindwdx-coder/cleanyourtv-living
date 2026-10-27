param(
    [ValidateSet('Scan','Helper','Install','SetupHome','RestoreHome','RestoreAerial','EndMaintenance')]
    [string]$Action = 'Scan',
    [string]$Serial,
    [int]$Port = 5038,
    [string]$StateDir,
    [string]$PauseFile,
    [string]$Adb,
    [string]$AndroidUserHome,
    [string]$Apk,
    [switch]$KeepAdb
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfigPath = Join-Path $taskRoot 'private/connection.json'
if (Test-Path -LiteralPath $taskConfigPath) {
    $taskConfig = Get-Content -LiteralPath $taskConfigPath -Raw | ConvertFrom-Json
    if (-not $Serial) { $Serial = $taskConfig.Serial }
    if (-not $PSBoundParameters.ContainsKey('Port')) { $Port = $taskConfig.Port }
    if (-not $StateDir) { $StateDir = $taskConfig.StateDir }
    if (-not $PauseFile) { $PauseFile = $taskConfig.PauseFile }
    if (-not $Adb) { $Adb = $taskConfig.Adb }
    if (-not $AndroidUserHome) { $AndroidUserHome = $taskConfig.AndroidUserHome }
}
if (-not $Serial) { throw 'Provide -Serial TV_IP:5555. Restore operations also need the original private snapshot.' }
if (-not $StateDir) { $StateDir = Join-Path $taskRoot 'private/backups' }
if (-not $Adb) { $Adb = (Get-Command adb -ErrorAction Stop).Source }
if (-not (Test-Path -LiteralPath $Adb -PathType Leaf)) { throw 'ADB is missing; provide -Adb.' }
if ($AndroidUserHome) { $env:ANDROID_USER_HOME = $AndroidUserHome }
$env:ADB_MDNS_AUTO_CONNECT = '0'
$taskArgs = @('--adb', $Adb, '--serial', $Serial, '--port', "$Port", '--state-dir', $StateDir)
switch ($Action) {
    'Scan' { $taskScript = 'clean_tv.py'; $taskArgs = @('scan') + $taskArgs }
    'Helper' { $taskScript = 'clean_tv.py'; $taskArgs = @('watch') + $taskArgs }
    'Install' {
        if (-not $Apk -or -not (Test-Path -LiteralPath $Apk -PathType Leaf)) { throw 'Provide -Apk with the APK you built and signed.' }
        $taskScript = 'clean_install.py'
        $taskArgs = @('install') + $taskArgs + @('--apk', $Apk)
    }
    'SetupHome' { $taskScript = 'clean_install.py'; $taskArgs = @('setup-home') + $taskArgs; if ($KeepAdb) { $taskArgs += '--keep-adb' } }
    'EndMaintenance' { $taskScript = 'clean_install.py'; $taskArgs = @('end-maintenance') + $taskArgs }
    'RestoreHome' { $taskScript = 'clean_install.py'; $taskArgs = @('restore-home') + $taskArgs }
    'RestoreAerial' {
        if (-not $PauseFile -or -not (Test-Path -LiteralPath $PauseFile -PathType Leaf)) { throw 'Original pause-aerial.json is required.' }
        $taskScript = 'restore_aerial.py'; $taskArgs += @('--pause-file', $PauseFile)
    }
}
& py -3.12 -X utf8 -B (Join-Path $PSScriptRoot $taskScript) @taskArgs
if ($LASTEXITCODE -ne 0) { throw "TV operation stopped with code $LASTEXITCODE; read the message above." }
