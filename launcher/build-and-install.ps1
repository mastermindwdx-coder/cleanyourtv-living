param([Parameter(Mandatory=$true)][string]$Serial,[string]$Adb='adb')
$ErrorActionPreference='Stop'
& "$PSScriptRoot/gradlew.bat" -p $PSScriptRoot --no-daemon assembleDebug
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
& python "$PSScriptRoot/../custom-tools/clean_install.py" install --adb $Adb --serial $Serial --apk "$PSScriptRoot/app/build/outputs/apk/debug/app-debug.apk"
if ($LASTEXITCODE -ne 0) { throw 'Install stopped; existing app and data preserved' }
Write-Output 'Ordinary application only. Read docs/INSTALL.md before enabling Home.'
