# ---------------------------------------------------------------------------------
# Script Name: DisableHonorSilentUpdateSoft.ps1
# Description: One-click script to disable silent updates (except PCManager main updates) and block domains
# ---------------------------------------------------------------------------------

# 1. Run as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    Exit
}

Write-Host "Running with Administrator privileges. Executing soft blocker strategies..." -ForegroundColor Green

# 2. Registry Block for Silent Components
function Set-RegistryValue {
    param (
        [string]$HivePath,
        [string]$Key,
        [object]$Value,
        [string]$Type = "DWord"
    )
    if (-not (Test-Path $HivePath)) {
        New-Item -Path $HivePath -Force | Out-Null
    }
    Set-ItemProperty -Path $HivePath -Name $Key -Value $Value -Type $Type -Force | Out-Null
}

$RegConfigs = @(
    @{ Path = "SOFTWARE\HONOR\MagicClaw\Setting"; Key = "IdleUpgrade"; Value = 0 },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\Setting\Local"; Key = "ServicePermission"; Value = 0 },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\Setting\Local"; Key = "AutoDownload"; Value = 0 },
    @{ Path = "SOFTWARE\HONOR\HUNTERCAMP"; Key = "ServicePermission"; Value = 0 },
    @{ Path = "SOFTWARE\HONOR\HUNTERCAMP"; Key = "AutoDownload"; Value = 0 },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\AISearch"; Key = "ServicePermission"; Value = 0 },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\AISearch"; Key = "AutoDownload"; Value = 0 },
    @{ Path = "SOFTWARE\Microsoft\Windows\CurrentVersion\Hihonornote"; Key = "SuitsService"; Value = 0 },
    @{ Path = "SOFTWARE\Microsoft\Windows\CurrentVersion\Hihonornote"; Key = "AgreeSilentUpdate"; Value = 0 },
    @{ Path = "SOFTWARE\DataMigration\HonorLoginGuide"; Key = "Protocol"; Value = 0 }
)

Write-Host "Injecting registry blocker policies..." -ForegroundColor Cyan
foreach ($config in $RegConfigs) {
    Set-RegistryValue -HivePath "HKCU:\$($config.Path)" -Key $config.Key -Value $config.Value
    Set-RegistryValue -HivePath "HKLM:\$($config.Path)" -Key $config.Key -Value $config.Value
}
Write-Host "Registry policies injected successfully." -ForegroundColor Green

# 3. Hosts Domain Blocking (Without configserver-drcn.platform.hihonorcloud.com to keep update working)
$HostsPath = "$env:windir\System32\drivers\etc\hosts"
$BlockDomains = @(
    "logservice-drcn.dt.hihonorcloud.com",
    "logservice-drcn.platform.hihonorcloud.com",
    "appcenter-drcn.platform.hihonorcloud.com",
    "hnid-drcn.cloud.hihonor.com"
)

Write-Host "Configuring Hosts domain blocks..." -ForegroundColor Cyan
if (Test-Path $HostsPath) {
    $BackupPath = "$HostsPath.bak"
    if (-not (Test-Path $BackupPath)) {
        Copy-Item -Path $HostsPath -Destination $BackupPath -Force
        Write-Host "Hosts file backup created at: hosts.bak" -ForegroundColor DarkGray
    }
}

$HostsContent = Get-Content -Path $HostsPath -Raw -ErrorAction SilentlyContinue
$NewEntries = [System.Text.StringBuilder]::new()

foreach ($domain in $BlockDomains) {
    if ($HostsContent -notmatch "(?m)^127\.0\.0\.1\s+$([regex]::Escape($domain))\s*(#.*)?$") {
        $NewEntries.AppendLine("127.0.0.1 $domain") | Out-Null
        Write-Host "  [Blocked] $domain" -ForegroundColor Yellow
    } else {
        Write-Host "  [Already Configured] $domain" -ForegroundColor DarkGray
    }
}

if ($NewEntries.Length -gt 0) {
    $BlockHeader = "`r`n# [Honor PCManager Silent Update Block]`r`n"
    Add-Content -Path $HostsPath -Value "$BlockHeader$($NewEntries.ToString())" -Force
    Write-Host "Hosts blocks written successfully." -ForegroundColor Green
} else {
    Write-Host "Hosts file is already up to date." -ForegroundColor Green
}

# 4. Terminate active processes to apply changes
Write-Host "Restarting background services to apply configurations..." -ForegroundColor Cyan
$ProcessNames = @("PCManager", "PCManagerTray", "HnUpdateService", "HnRSMService", "HnFrontNavigator", "HnMagicClawUI")
foreach ($proc in $ProcessNames) {
    Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
}

Stop-Service -Name "HnUpdateService" -Force -ErrorAction SilentlyContinue
Stop-Service -Name "HnRSMService" -Force -ErrorAction SilentlyContinue
ipconfig /flushdns | Out-Null

Write-Host "All blocker strategies successfully deployed!" -ForegroundColor Green
Write-Host "Exiting in 3 seconds..." -ForegroundColor DarkGray
Start-Sleep -Seconds 3
